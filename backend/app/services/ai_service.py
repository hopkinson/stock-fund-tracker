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

    async def analyze_portfolio(self, positions_data: List[Dict[str, Any]], summary: Dict[str, Any], custom_prompt: str = "") -> str:
        api_key = self.api_key or os.getenv("AI_API_KEY")
        if not api_key:
            return "⚠️ 未配置 AI API Key。请在系统右上角「AI 复盘」中配置 API Key（推荐 DeepSeek 或 通义千问）。"

        index_items = await self.get_index_valuations()

        formatted_lines = []
        etf_count = 0
        total_count = len(positions_data)

        for p in positions_data[:20]:
            name = p.get('name', '')
            code = p.get('code', '')
            is_etf = p.get('is_etf', False) or "ETF" in name or "指数" in name or code.startswith(('51', '15', '56', '58', '16'))
            if is_etf:
                etf_count += 1

            line = f"- 【{name} ({code})】"
            if is_etf:
                line += " [ETF/指数标的]"
            
            line += f": 现价 ¥{p.get('current_price')}, 今日涨跌 {p.get('today_profit_rate')}%, 今日盈亏 ¥{p.get('today_profit')}, 累计收益率 {p.get('total_profit_rate')}%"

            # 场内折溢价率 (针对ETF)
            premium = p.get("premium_rate", 0.0)
            iopv = p.get("iopv", 0.0)
            if is_etf:
                if iopv > 0:
                    line += f", IOPV净值: {iopv}"
                if abs(premium) > 0.01:
                    prem_tag = "⚠️高溢价风险!" if premium > 1.0 else ("折价安全垫" if premium < -0.5 else "正常")
                    line += f", 场内折溢价: {premium}%({prem_tag})"

            # 关联指数估值与历史百分位
            matched = self.match_index(name, code, index_items)
            if matched:
                idx_name = matched.get("name")
                pe = matched.get("pe", 0)
                pe_pct = round(matched.get("pe_percentile", 0) * 100, 1)
                pb_pct = round(matched.get("pb_percentile", 0) * 100, 1)
                eva = matched.get("eva_type", "mid")
                eva_str = "低估定投区" if eva == "low" else ("高估风险区" if eva == "high" else "合理持有区")
                yeild = round(matched.get("yeild", 0) * 100, 2)
                line += f"\n  ↳ 跟踪指数: {idx_name} | PE: {pe} (历史分位 {pe_pct}%, {eva_str}) | 股息率: {yeild}%"

            formatted_lines.append(line)

        pos_summary = "\n".join(formatted_lines)
        is_mainly_etf = (etf_count / max(total_count, 1)) >= 0.4

        if is_mainly_etf:
            system_msg = (
                "你是一名拥有20年实战经验的顶级全球宏观对冲基金 CIO（首席投资官）与大类资产/ETF 指数配置专家。"
                "你面对的是以【ETF 与指数基金】为核心持仓的投资者。ETF 投资无需阅读企业财报，核心关注：指数历史估值分位、大类资产配置比例、行业重叠度与场内折溢价风险。"
                "\n"
                "复盘要求：态度犀利、专业、务实，拒绝空洞套话，按以下维度进行硬核复盘：\n"
                "1. 【大类配置与集中度】：检查持仓结构（宽基底仓、行业主题、跨境ETF、红利防守），诊断是否存在“看似分散实则同涨同跌”的伪分散风险；\n"
                "2. 【指数估值水位与性价比】：结合提供的 PE 历史百分位（<20% 低估黄金坑，20%-70% 适中持有，>80% 泡沫偏贵），明确指出哪些标的性价比最高、哪些处于高风险区；\n"
                "3. 【场内折溢价排雷】：若有 ETF 出现场内显著正溢价（尤其跨境或热门标的），严肃警示溢价抹平杀伤力；\n"
                "4. 【实操策略与纪律】：给出清晰明确的定投节奏、网格补仓点位或止盈建议，督促恪守交易纪律。"
            )
        else:
            system_msg = (
                "你是一名拥有20年实战经验的顶级量化基金投资总监与老操盘手。"
                "根据用户的实盘持仓与盈亏数据，进行简练、犀利、专业的复盘诊断。"
                "禁止假大空的客套话，重点指出：1.今日盈亏的核心归因与仓位风险点；2.技术面与估值面建议；3.交易纪律提醒。"
            )

        user_content = (
            f"我的当前总资产: ¥{summary.get('total_asset')}, 今日总盈亏: ¥{summary.get('today_profit')} ({summary.get('today_profit_rate')}%)\n"
            f"持仓明细与估值指标:\n{pos_summary}\n\n"
            f"{custom_prompt or '请为我的持仓做专业复盘，重点分析ETF估值水位、大类资产集中度，并给出定投或止盈风控建议。'}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.6,
            "max_tokens": 1000
        }

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
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

ai_service = AIService()
