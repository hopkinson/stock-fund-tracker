import os
import time
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        # 支持 DeepSeek / Qwen / OpenAI 等任意 OpenAI 兼容接口，默认 DeepSeek
        self.api_key = os.getenv("AI_API_KEY", "")
        self.api_base = os.getenv("AI_API_BASE", "https://api.deepseek.com/v1")
        self.model = os.getenv("AI_MODEL", "deepseek-chat")
        
        # 缓存指数估值数据 (1小时过期)
        self._index_cache: List[Dict[str, Any]] = []
        self._index_cache_time: float = 0

    async def get_index_valuations(self) -> List[Dict[str, Any]]:
        """获取全市场主要指数估值与历史百分位 (蛋卷基金公募接口)"""
        now = time.time()
        if self._index_cache and (now - self._index_cache_time < 3600):
            return self._index_cache

        url = "https://danjuanfunds.com/djapi/index_eva/dj"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", {}).get("items", [])
                    if items:
                        self._index_cache = items
                        self._index_cache_time = now
                        return items
        except Exception as e:
            print(f"[AIService] fetch index valuation error: {e}")

        return self._index_cache

    def match_index(self, name: str, code: str, index_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """将持仓标的 (尤其是ETF或指数基金) 模糊匹配至跟踪指数估值"""
        clean_name = name.replace("ETF", "").replace("易方达", "").replace("华泰柏瑞", "").replace("华夏", "")
        clean_name = clean_name.replace("广发", "").replace("南方", "").replace("天弘", "").replace("富国", "").strip()

        # 关键词精确权重匹配
        alias_map = {
            "300": "沪深300",
            "500": "中证500",
            "1000": "中证1000",
            "2000": "中证2000",
            "50": "上证50",
            "科创": "科创50",
            "创业板": "创业板",
            "券商": "证券公司",
            "证券": "证券公司",
            "白酒": "中证白酒",
            "酒": "中证白酒",
            "食品": "国证食品",
            "消费": "主要消费",
            "医疗": "中证医疗",
            "医药": "全指医药",
            "红利": "中证红利",
            "低波": "500低波",
            "银行": "中证银行",
            "地产": "国证地产",
            "房地产": "国证地产",
            "芯片": "半导体",
            "半导体": "半导体",
            "纳指": "纳指100",
            "纳斯达克": "纳指100",
            "标普": "标普500",
            "恒生科技": "恒生科技",
            "恒生": "恒生指数",
            "中概": "中概互联",
            "军工": "中证军工",
            "光伏": "光伏产业",
            "有色": "国证有色",
            "煤炭": "中证煤炭",
            "5G": "5G通讯",
            "传媒": "中证传媒",
        }

        # 1. 尝试关键词直接定位
        target_keyword = None
        for k, v in alias_map.items():
            if k in clean_name or k in name:
                target_keyword = v
                break

        for item in index_items:
            idx_name = item.get("name", "")
            if target_keyword and (target_keyword in idx_name or idx_name in target_keyword):
                return item
            if clean_name and (clean_name in idx_name or idx_name in clean_name):
                return item

        return None

    async def analyze_portfolio(
        self,
        positions_data: List[Dict[str, Any]],
        summary: Dict[str, Any],
        custom_prompt: str = "",
        focus_areas: Optional[List[str]] = None,
        investment_style: Optional[str] = "balanced",
        detail_level: Optional[str] = "detailed"
    ) -> str:
        api_key = self.api_key or os.getenv("AI_API_KEY")
        if not api_key:
            return "⚠️ 未配置 AI 接口密钥。请在弹窗右上角「配置」中填入 API Key（推荐使用 DeepSeek 或兼容接口）。"

        if not positions_data:
            return "⚠️ 当前未选中任何持仓。请确保账户中有持仓数据，或在上方勾选需要分析的股票/基金。"

        index_items = await self.get_index_valuations()

        formatted_lines = []
        total_asset = summary.get('total_asset', 0) or 1.0

        for p in positions_data[:30]:
            name = p.get('name', '')
            code = p.get('code', '')
            is_etf = p.get('is_etf', False) or "ETF" in name or "指数" in name or code.startswith(('51', '15', '56', '58', '16'))
            mv = p.get('market_value', 0) or 0
            weight = p.get('weight')
            if weight is None:
                weight = round((mv / max(total_asset, 1.0)) * 100, 1)
            cost = p.get('cost_price', 0) or 0
            price = p.get('current_price', 0) or 0
            today_rate = p.get('today_profit_rate', 0) or 0
            total_rate = p.get('total_profit_rate', 0) or 0
            today_p = p.get('today_profit', 0) or 0
            total_p = p.get('total_profit', 0) or 0
            shares = p.get('shares', 0) or 0

            type_tag = "[ETF/基金]" if is_etf else "[股票]"
            line = (
                f"- 【{name} ({code})】{type_tag}：\n"
                f"  当前市值 ¥{mv:,.2f} (占总资产 {weight}%) | 持有 {shares} 股/份\n"
                f"  买入成本 ¥{cost:.3f} | 当前现价 ¥{price:.3f}\n"
                f"  今日涨跌 {today_rate:+.2f}% (今日盈亏 ¥{today_p:+.2f}) | 累计盈亏率 {total_rate:+.2f}% (累计盈亏 ¥{total_p:+.2f})"
            )

            # 场内折溢价率 (针对ETF)
            premium = p.get("premium_rate", 0.0) or 0.0
            iopv = p.get("iopv", 0.0) or 0.0
            if is_etf:
                if iopv > 0:
                    line += f"\n  ↳ IOPV估算净值: {iopv:.4f}"
                if abs(premium) > 0.01:
                    prem_tag = "⚠️溢价过高风险!" if premium > 1.0 else ("折价安全垫" if premium < -0.5 else "正常")
                    line += f" | 场内折溢价: {premium:+.2f}% ({prem_tag})"

            # 关联指数估值与历史百分位
            matched = self.match_index(name, code, index_items)
            if matched:
                idx_name = matched.get("name")
                pe = matched.get("pe", 0)
                pe_pct = round(matched.get("pe_percentile", 0) * 100, 1)
                eva = matched.get("eva_type", "mid")
                eva_str = "低估定投区" if eva == "low" else ("高估风险区" if eva == "high" else "合理持有区")
                yeild = round(matched.get("yeild", 0) * 100, 2)
                line += f"\n  ↳ 跟踪指数: {idx_name} | PE: {pe} (历史分位 {pe_pct}%, {eva_str}) | 股息率: {yeild}%"

            formatted_lines.append(line)

        pos_summary = "\n\n".join(formatted_lines)

        # 投资风格描述
        style_desc = {
            "conservative": "稳健防守型（风险承受力较低，优先控制回撤与保本，注重安全边际与分红）",
            "balanced": "均衡配置型（兼顾稳健与收益，核心宽基+适度行业轮动，注重中长线配置）",
            "aggressive": "积极进取型（能承受较大短期波动，追求超额收益与成长弹性，紧跟市场主线）"
        }.get(investment_style, "均衡配置型")

        # 关注重点描述
        focus_dict = {
            "loss_recovery": "重点诊断浮亏持仓与解套策略（深入分析套牢资产的成因，明确是该逢低补仓拉平成本、调仓换股还是继续持有）",
            "position_risk": "重点排查仓位与集中度风险（诊断单一重仓比例是否过高、资产结构是否合理、是否存在同涨同跌的假分散）",
            "valuation": "重点分析估值性价比与加仓时机（结合指数历史PE分位与折溢价，明确指出哪些处于低估机会区、哪些偏贵不宜追高）",
            "trade_points": "重点给出明确买卖与操作点位建议（给出具体的加减仓分批节奏、关键支撑/阻力参考与止盈止损点）"
        }
        focus_texts = [focus_dict[k] for k in (focus_areas or []) if k in focus_dict]
        focus_summary = "；\n".join(focus_texts) if focus_texts else "综合诊断持仓合理性、仓位风险与后续调仓策略"

        # 报告深度
        depth_instruction = (
            "请提供精炼直白的要点清单，2分钟内可读完，直接给核心结论与明确操作行动点。"
            if detail_level == "concise" else
            "请提供深入透彻的持仓体检，务必对用户选中的具体持仓逐一分析成本、盈亏与具体应对策略。"
        )

        system_msg = (
            "你是一位实战经验丰富、客观理性的个人投资与资产配置助手。\n"
            "你的任务是根据用户提供的【真实持仓明细（包含每只标的的代码、名称、买入成本、现价、累计盈亏、仓位占比、指数估值分位与折溢价）】，进行精准、务实、接地气的持仓诊断与操作建议。\n\n"
            "必须严格遵守以下原则：\n"
            "1. 【紧密结合真实持仓】：严禁脱离持仓空谈大道理！必须直接指名道姓分析用户的具体股票/基金，直接结合用户的实际成本价、浮盈浮亏金额与仓位占比给出判断。\n"
            "2. 【通俗易懂，拒绝金融黑话】：不要使用任何虚浮概念（如‘CIO级诊断’、‘在管标的’、‘战报’等），用普通投资者一听就懂的大白话交流，真诚自然。\n"
            "3. 【针对性强】：严格围绕用户的投资风格与指定的关注重点给出具体操作建议。\n"
            "4. 【结构分明】：按照以下模块结构化输出（使用清晰的 Markdown 标题与列表）：\n"
            "   - 📊 【持仓整体诊断】：整体仓位健康度、资产分布是否合理、最大风险点在哪里；\n"
            "   - 🔍 【重点持仓逐一诊断】：针对主要持仓，结合成本价与现价，明确分析现状与应对思路；\n"
            "   - 🎯 【具体操作与调仓建议】：明确指出下一步该做什么（哪些建议持有等待、哪些可以分批定投/加仓、哪些建议冲高减仓或止盈，并给出具体的参考区间或纪律）。"
        )

        user_content = (
            f"【我的资产概况】\n"
            f"- 总资产: ¥{summary.get('total_asset', 0):,.2f}\n"
            f"- 今日盈亏: ¥{summary.get('today_profit', 0):+,.2f} ({summary.get('today_profit_rate', 0):+.2f}%)\n"
            f"- 累计盈亏: ¥{summary.get('total_profit', 0):+,.2f} ({summary.get('total_profit_rate', 0):+.2f}%)\n"
            f"- 本次分析持仓数量: {len(positions_data)} 只\n\n"
            f"【我的投资偏好】\n"
            f"- 投资风格: {style_desc}\n"
            f"- 分析重点:\n{focus_summary}\n"
            f"- 分析深度: {depth_instruction}\n\n"
            f"【本次纳入分析的持仓明细】\n{pos_summary}\n\n"
            f"【我的补充要求 / 特定疑问】\n{custom_prompt if custom_prompt else '请根据上述实际持仓，给出精准中肯的分析与具体操作建议。'}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.5,
            "max_tokens": 2500
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.api_base.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload
                )
                if resp.status_code != 200:
                    return f"AI 接口响应异常 ({resp.status_code}): {resp.text}"
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"调用 AI 服务失败: {str(e)}"

    @property
    def is_configured(self) -> bool:
        return bool(os.getenv("AI_API_KEY", self.api_key).strip())

    async def chat_completion(self, prompt: str, system_prompt: str = "你是一位客观理性的投资助手，用大白话交流，严禁喊买卖，注重防追高风险。") -> str:
        api_key = os.getenv("AI_API_KEY", self.api_key)
        if not api_key:
            return ""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4,
            "max_tokens": 800
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.api_base.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[AIService] chat_completion error: {e}")
        return ""

ai_service = AIService()

