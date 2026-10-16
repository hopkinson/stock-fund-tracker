import re
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.quote_service import quote_service
from app.services.ai_service import ai_service
from app.services.notify_service import notify_service

class KOLTrackerService:
    def __init__(self):
        self.sina_news_url = "https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=40&zhibo_id=152"
        self.eastmoney_news_url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

    async def _fetch_sina_news(self, client: httpx.AsyncClient, limit: int = 25) -> List[Dict[str, str]]:
        """拉取新浪 7x24 宏观与大盘快讯"""
        try:
            resp = await client.get(self.sina_news_url)
            if resp.status_code == 200:
                feed_list = resp.json().get("result", {}).get("data", {}).get("feed", {}).get("list", [])
                items = []
                for item in feed_list:
                    raw_text = item.get("rich_text", "") or item.get("text", "")
                    clean_text = re.sub(r"<[^>]+>", "", raw_text).strip()
                    create_time = item.get("create_time", "")
                    if clean_text:
                        items.append({"source": "新浪财经", "time": create_time, "text": clean_text})
                    if len(items) >= limit:
                        break
                return items
        except Exception as e:
            print(f"[News] fetch sina error: {e}")
        return []

    async def _fetch_eastmoney_news(self, client: httpx.AsyncClient, limit: int = 25) -> List[Dict[str, str]]:
        """拉取东方财富 7x24 A股与行业快讯"""
        try:
            resp = await client.get(self.eastmoney_news_url)
            if resp.status_code == 200:
                text = resp.text.replace("var ajaxResult=", "").strip().rstrip(";")
                data = json.loads(text)
                lives = data.get("LivesList", [])
                items = []
                for item in lives:
                    title = item.get("title", "")
                    digest = item.get("digest", "")
                    show_time = item.get("showtime", "")
                    full_text = f"{title}：{digest}" if (title and digest and title != digest) else (title or digest)
                    full_text = re.sub(r"<[^>]+>", "", full_text).strip()
                    if full_text:
                        items.append({"source": "东方财富", "time": show_time, "text": full_text})
                    if len(items) >= limit:
                        break
                return items
        except Exception as e:
            print(f"[News] fetch eastmoney error: {e}")
        return []

    async def get_latest_7x24_news(self, keyword: str = "", limit: int = 25) -> List[Dict[str, str]]:
        """
        多源并行聚合拉取（新浪宏观 + 东方财富A股行业）：
        毫秒级异步并发，利用文本指纹自动排重，按时间倒序混排
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=5.0) as client:
                res_sina, res_em = await asyncio.gather(
                    self._fetch_sina_news(client, limit=limit),
                    self._fetch_eastmoney_news(client, limit=limit),
                    return_exceptions=True
                )
                raw_list = [item for r in (res_sina, res_em) if isinstance(r, list) for item in r]

                # 简单指纹排重（取清洗后前 14 个有效字符）
                seen_signatures = set()
                deduped = []
                for item in raw_list:
                    text = item["text"]
                    if keyword:
                        clean_kw = keyword.replace("ETF", "").replace("中证", "").replace("指数", "").strip()
                        if clean_kw and clean_kw not in text:
                            continue

                    sig = re.sub(r"[\s\W_]+", "", text)[:14]
                    if sig and sig not in seen_signatures:
                        seen_signatures.add(sig)
                        deduped.append(item)

                # 按时间降序排序
                deduped.sort(key=lambda x: x.get("time", ""), reverse=True)
                return deduped[:limit]
        except Exception as e:
            print(f"[News] multi-source error: {e}")
            return []

    async def get_market_trends_overview(self) -> Dict[str, Any]:
        """
        全自动市场风向与板块动态概览（零人工输入）：
        1. 自动拉取核心宽基与热门行业 ETF 实时表现
        2. 结合估值分位客观评判，坚决不无脑喊买卖，重点做防追高提示
        3. 聚合最新 7x24 多源财经快讯
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

        board_list.sort(key=lambda x: x["change_rate"], reverse=True)

        latest_news = await self.get_latest_7x24_news(limit=20)

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

    async def generate_and_push_daily_recap(self, db: Session):
        """
        盘后 15:30 AI 自动提炼全天大事解读与冷静观察，推送到微信
        """
        data = await self.get_market_trends_overview()
        news = data.get("news", [])[:10]
        boards = data.get("boards", [])

        # 整理要点
        top_gainers = [b for b in boards if b["change_rate"] > 1.5][:3]
        hot_warning = ""
        if top_gainers:
            hot_warning = f"⚠️ 今日领涨的 {', '.join([g['name'] for g in top_gainers])} 短期波动较大，切勿因热门盲目追高。\n"

        news_text = "\n".join([f"- **[{n.get('source', '快讯')}]** {n['text']}" for n in news[:5]])

        # 尝试调用大模型提炼；若未配 Key 或调用失败，优雅回退本地通俗总结
        ai_summary = data.get("summary", "")
        if ai_service.is_configured:
            prompt = (
                f"这是今天的市场板块表现和精选大事：\n"
                f"板块概况：{data.get('summary')}\n"
                f"最新要闻：{news_text}\n\n"
                f"请用普通投资者能听懂的大白话，输出一份收盘解读：\n"
                f"1. 用2-3句话总结今天市场核心大势；\n"
                f"2. 指出对主要板块的影响；\n"
                f"3. 严肃做防追高提醒（严禁喊买卖，严禁吹捧大涨板块）。总字数在 150 字以内。"
            )
            try:
                ai_res = await ai_service.chat_completion(prompt)
                if ai_res:
                    ai_summary = ai_res.strip()
            except Exception as e:
                print(f"[DailyRecap] AI call failed, fallback to local summary: {e}")

        content_lines = [
            f"### 📢 收盘大事与冷静观察",
            f"> 聚合新浪 + 东方财富 7x24 优质资讯流 | {datetime.now().strftime('%m月%d日 15:30')}\n",
            f"#### 💡 今日 AI 白话解读",
            f"{ai_summary}\n",
            hot_warning,
            f"#### 🌐 盘后精选大事",
            news_text
        ]
        markdown_body = "\n".join(filter(None, content_lines))
        await notify_service.send_notification("📢 收盘大事与冷静观察", markdown_body, db, event_type="market_recap")

kol_tracker_service = KOLTrackerService()
