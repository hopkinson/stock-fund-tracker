import re
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.quote_service import quote_service
from app.services.ai_service import ai_service
from app.services.notify_service import notify_service

# 常见热门 ETF 别名映射 (按关键词长度降序优先匹配)
ETF_ALIAS_MAP = {
    "中证A500": "159338", "A500": "159338",
    "沪深300": "510300",
    "中证500": "510500",
    "中证1000": "512100",
    "中证2000": "159531",
    "科创50": "588000",
    "创业板50": "159681", "创50": "159681", "创业板": "159915",
    "恒生科技": "513180", "恒科": "513180",
    "恒生指数": "159920", "港股通": "513090",
    "中概互联": "513050",
    "红利低波": "512890", "中证红利": "515080",
    "纳斯达克": "513100", "纳指": "513100",
    "标普500": "513500",
    "半导体": "512480", "芯片": "159995",
    "白酒": "512690",
    "主要消费": "159928", "食品饮料": "516900",
    "中证医疗": "512170", "医药": "512010",
    "证券公司": "512880", "券商": "512000",
    "军工": "512660", "光伏": "515790",
    "银行": "512800", "有色金属": "512400", "煤炭": "515220"
}

BUY_KEYWORDS = ["买入", "加仓", "定投", "建仓", "低吸", "补仓", "申购", "上车", "抄底"]
SELL_KEYWORDS = ["卖出", "减仓", "止盈", "清仓", "高抛", "止损", "赎回", "下车", "减持"]

class KOLTrackerService:
    def __init__(self):
        self.sina_news_url = "https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=40&zhibo_id=152"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

    def extract_trades_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从博主文案中纯正则匹配 ETF 代码与操作方向"""
        text = text.strip()
        if not text:
            return []

        found_codes = set()
        # 1. 匹配标准 6 位场内基金代码 (51, 15, 56, 58, 16 开头)
        matched_digits = re.findall(r"\b(15\d{4}|51\d{4}|56\d{4}|58\d{4}|16\d{4})\b", text)
        for code in matched_digits:
            found_codes.add(code)

        # 2. 匹配中文俗名
        for name, code in ETF_ALIAS_MAP.items():
            if name in text:
                found_codes.add(code)

        if not found_codes:
            return []

        # 3. 提取买卖动作
        action = "BUY" if any(k in text for k in BUY_KEYWORDS) else ("SELL" if any(k in text for k in SELL_KEYWORDS) else "HOLD")

        # 4. 提取价格 (可选，如 "成本 1.05", "现价1.2元")
        price_match = re.search(r"(?:成本|买入价|成交价|价格|现价)[：:\s]*([0-9]+\.?[0-9]*)", text)
        specified_price = float(price_match.group(1)) if price_match else None

        results = []
        for code in found_codes:
            results.append({
                "code": code,
                "action": action,
                "specified_price": specified_price
            })
        return results

    async def get_latest_7x24_news(self, keyword: str = "", limit: int = 3) -> List[Dict[str, str]]:
        """获取新浪 7x24 全球财经快讯，并可按关键词或板块过滤"""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=5.0) as client:
                resp = await client.get(self.sina_news_url)
                if resp.status_code == 200:
                    data = resp.json()
                    feed_list = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
                    news_items = []
                    for item in feed_list:
                        raw_text = item.get("rich_text", "") or item.get("text", "")
                        clean_text = re.sub(r"<[^>]+>", "", raw_text).strip()
                        create_time = item.get("create_time", "")
                        if not clean_text:
                            continue

                        # 如果有关键词要求，进行匹配过滤
                        if keyword:
                            clean_kw = keyword.replace("ETF", "").replace("中证", "").replace("指数", "").strip()
                            if clean_kw and clean_kw in clean_text:
                                news_items.append({"time": create_time, "text": clean_text})
                        else:
                            news_items.append({"time": create_time, "text": clean_text})

                        if len(news_items) >= limit:
                            break

                    return news_items
        except Exception as e:
            print(f"[KOLTracker] fetch sina news error: {e}")
        return []

    async def analyze_blogger_post(self, content: str, blogger_name: str = "小红书博主") -> Dict[str, Any]:
        """
        核心交叉验证引擎：
        博主操作 + 实时行情 + 蛋卷指数估值(PE历史分位) + 7x24 宏观快讯 -> 综合研报
        """
        trades = self.extract_trades_from_text(content)
        if not trades:
            return {
                "success": False,
                "message": "未能从文案中识别出有效的 ETF 代码或标的，请确认是否包含 ETF 代码(如 159338) 或常见简称(如 A500/恒科)。",
                "trades": [],
                "report_markdown": ""
            }

        codes = [t["code"] for t in trades]
        # 批量获取真实行情
        quotes = await quote_service.get_stock_quotes(codes)
        # 批量获取指数估值
        evaluations = await ai_service.get_index_valuations()

        analyzed_trades = []
        report_lines = [
            f"### 🔍 KOL 调仓验真研报",
            f"> **监控对象**：{blogger_name}",
            f"> **识别标的数**：{len(codes)} 只 | **分析时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        ]

        for t in trades:
            code = t["code"]
            q = quotes.get(code, {})
            name = q.get("name", f"ETF-{code}")
            curr_price = float(q.get("current_price", 0.0))
            change_rate = float(q.get("change_rate", 0.0))
            action = t["action"]
            action_desc = "🟢 【买入/加仓】" if action == "BUY" else ("🔴 【卖出/止盈】" if action == "SELL" else "⚪ 【观望/提及】")

            # 匹配估值数据
            matched_idx = ai_service.match_index(name, code, evaluations)
            pe_pct = round(matched_idx.get("pe_percentile", 0.0) * 100, 1) if matched_idx else None
            idx_name = matched_idx.get("name", "对应指数") if matched_idx else "未知指数"
            pe_val = matched_idx.get("pe", "-") if matched_idx else "-"

            # 评估估值水位
            if pe_pct is not None:
                if pe_pct < 25:
                    eva_level = "低估黄金坑 (安全边际高)"
                elif pe_pct > 75:
                    eva_level = "高估风险区 (情绪过热)"
                else:
                    eva_level = "合理持有区"
            else:
                eva_level = "估值分位未收录"

            # 抓取相关新闻
            news_items = await self.get_latest_7x24_news(keyword=name, limit=1)
            news_brief = news_items[0]["text"] if news_items else "今日该板块无重大异动快讯"

            # 决策打分
            if action == "BUY":
                if pe_pct is not None and pe_pct < 25:
                    verdict = "🎯 **强烈共振跟投**：标的处于低估黄金坑，博主加仓具有较高安全边际。"
                elif pe_pct is not None and pe_pct > 75:
                    verdict = "⚠️ **警惕高位接盘**：标的处于历史高估区，博主追高风险大，切勿盲目抄作业！"
                else:
                    verdict = "📊 **中性关注**：估值处于适中区间，建议按既定定投节奏分批布局。"
            elif action == "SELL":
                if pe_pct is not None and pe_pct > 70:
                    verdict = "🛡️ **合理止盈**：估值已达相对高位，博主落袋为安策略审慎合规。"
                else:
                    verdict = "🔄 **减仓调仓**：博主降低敞口，注意观察板块资金承接。"
            else:
                verdict = "👀 **保持跟踪**：未发现明确买卖指令。"

            analyzed_trades.append({
                "code": code,
                "name": name,
                "action": action,
                "current_price": curr_price,
                "change_rate": change_rate,
                "index_name": idx_name,
                "pe": pe_val,
                "pe_percentile": pe_pct,
                "eva_level": eva_level,
                "news": news_brief,
                "verdict": verdict
            })

            report_lines.append(f"#### 📌 {name} ({code}) {action_desc}")
            report_lines.append(f"- **实时行情**：现价 ¥{curr_price:.3f} (今日涨跌: `{change_rate:+.2f}%`)")
            if pe_pct is not None:
                report_lines.append(f"- **估值水位**：PE `{pe_val}` (历史分位 **{pe_pct}%** - `{eva_level}`)")
            report_lines.append(f"- **板块快讯**：{news_brief}")
            report_lines.append(f"- **综合验真**：{verdict}\n")

        return {
            "success": True,
            "blogger_name": blogger_name,
            "trades": analyzed_trades,
            "report_markdown": "\n".join(report_lines)
        }

    async def push_analysis_to_wechat(self, report_markdown: str, db: Session):
        """将验真研报推送到微信 PushPlus"""
        return await notify_service.send_notification(
            title="🔔 KOL 调仓验真研报",
            content_markdown=report_markdown,
            db=db,
            event_type="alert"
        )

kol_tracker_service = KOLTrackerService()
