import re
import httpx
from datetime import datetime
from typing import Dict, Any, List

from app.services.quote_service import quote_service
from app.services.ai_service import ai_service

class KOLTrackerService:
    def __init__(self):
        self.sina_news_url = "https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=40&zhibo_id=152"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

    async def get_latest_7x24_news(self, keyword: str = "", limit: int = 20) -> List[Dict[str, str]]:
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

    async def get_market_trends_overview(self) -> Dict[str, Any]:
        """
        全自动市场风向与板块动态概览（零人工输入）：
        1. 自动拉取核心宽基与热门行业 ETF 实时表现
        2. 结合估值分位客观评判，坚决不无脑喊买卖，重点做防追高提示
        3. 聚合最新 7x24 财经快讯
        """
        watch_targets = [
            {"code": "159338", "name": "中证A500", "category": "核心宽基"},
            {"code": "510300", "name": "沪深300", "category": "核心宽基"},
            {"code": "588000", "name": "科创50", "category": "核心宽基"},
            {"code": "513180", "name": "恒生科技", "category": "热门科技"},
            {"code": "512480", "name": "半导体", "category": "热门科技"},
            {"code": "513050", "name": "中概互联", "category": "热门科技"},
            {"code": "512890", "name": "红利低波", "category": "价值防守"},
            {"code": "512800", "name": "银行", "category": "价值防守"},
            {"code": "512000", "name": "券商", "category": "金融周期"},
            {"code": "512690", "name": "白酒", "category": "大消费"},
            {"code": "512010", "name": "医药", "category": "医药医疗"},
            {"code": "518880", "name": "黄金ETF", "category": "大宗防守"},
            {"code": "513500", "name": "标普500", "category": "海外资产"},
        ]

        codes = [t["code"] for t in watch_targets]
        quotes = await quote_service.get_stock_quotes(codes)
        evaluations = await ai_service.get_index_valuations()

        board_list = []
        for item in watch_targets:
            code = item["code"]
            q = quotes.get(code, {})
            name = q.get("name", item["name"])
            curr_price = float(q.get("current_price", 0.0))
            change_rate = float(q.get("change_rate", 0.0))

            matched_idx = ai_service.match_index(name, code, evaluations)
            pe_pct = round(matched_idx.get("pe_percentile", 0.0) * 100, 1) if matched_idx else None
            pe_val = matched_idx.get("pe", "-") if matched_idx else "-"

            # 防追高与客观状态评估（绝不喊买卖）
            if change_rate > 2.0:
                if pe_pct is not None and pe_pct > 70:
                    status_tag = "短期涨幅偏大·估值偏高"
                    status_type = "warning"
                    hint = "板块当前热度高但处于高位，切忌跟风追涨，谨防冲高回落。"
                else:
                    status_tag = "强势拉升"
                    status_type = "up"
                    hint = "今日涨幅突出，保持客观观察，不必追单。"
            elif change_rate < -2.0:
                if pe_pct is not None and pe_pct < 30:
                    status_tag = "低位调整·估值低"
                    status_type = "low_opp"
                    hint = "估值分位处于相对低位，回调中可关注企稳信号，避免恐慌。"
                else:
                    status_tag = "走弱调整"
                    status_type = "down"
                    hint = "短线回调中，注意防守。"
            else:
                status_tag = "窄幅震荡"
                status_type = "neutral"
                hint = "走势平稳，估值合理，按原有节奏观察即可。"

            board_list.append({
                "code": code,
                "name": name,
                "category": item["category"],
                "current_price": curr_price,
                "change_rate": change_rate,
                "pe": pe_val,
                "pe_percentile": pe_pct,
                "status_tag": status_tag,
                "status_type": status_type,
                "hint": hint
            })

        # 按今日涨跌幅降序排列
        board_list.sort(key=lambda x: x["change_rate"], reverse=True)

        latest_news = await self.get_latest_7x24_news(limit=15)

        top_gainers = [b for b in board_list if b["change_rate"] > 0][:3]
        top_losers = [b for b in board_list if b["change_rate"] < 0][-3:]
        
        gainers_str = "、".join([f"{g['name']}({g['change_rate']:+.2f}%)" for g in top_gainers]) if top_gainers else "暂无"
        losers_str = "、".join([f"{l['name']}({l['change_rate']:+.2f}%)" for l in top_losers]) if top_losers else "暂无"

        overview_summary = (
            f"今日领涨板块主要为 {gainers_str}，调整板块主要为 {losers_str}。"
            f" 市场板块轮动常态化，切忌因为某板块今天涨得好就急着跟风追高；重点关注估值水位与资产分散配置，理性看待涨跌。"
        )

        return {
            "success": True,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": overview_summary,
            "boards": board_list,
            "news": latest_news
        }

kol_tracker_service = KOLTrackerService()
