import re
import json
import time
import httpx
from typing import Dict, List, Optional, Any

class QuoteService:
    def __init__(self):
        self.qq_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://finance.qq.com"
        }
        self.sina_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://finance.sina.com.cn"
        }

    @staticmethod
    def format_stock_symbol(code: str) -> str:
        """根据股票代码自动添加 sh / sz / bj 前缀"""
        code = str(code).strip()
        if code.startswith(("sh", "sz", "bj")):
            return code
        if code.startswith(("60", "68", "11", "51", "58")):
            return f"sh{code}"
        elif code.startswith(("00", "30", "12", "15", "16")):
            return f"sz{code}"
        elif code.startswith(("8", "4", "92")):
            return f"bj{code}"
        elif len(code) == 5 and code.isdigit():
            return f"hk{code}"
        return f"sz{code}"

    async def get_stock_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取股票/ETF实时行情 (腾讯行情接口)"""
        if not symbols:
            return {}

        formatted_map = {self.format_stock_symbol(code): code for code in symbols}
        query_param = ",".join(formatted_map.keys())
        url = f"http://qt.gtimg.cn/q={query_param}"

        results = {}
        try:
            async with httpx.AsyncClient(headers=self.qq_headers, timeout=6.0) as client:
                resp = await client.get(url)
                text = resp.content.decode("gbk", errors="ignore")

                for line in text.split(";"):
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    left, right = line.split("=", 1)
                    raw_symbol = left.replace("v_", "").strip()
                    original_code = formatted_map.get(raw_symbol, raw_symbol[2:])
                    content = right.strip('"\r\n ')
                    fields = content.split("~")
                    if len(fields) > 35:
                        name = fields[1]
                        code = fields[2]
                        current_price = float(fields[3]) if fields[3] else 0.0
                        last_close = float(fields[4]) if fields[4] else 0.0
                        open_price = float(fields[5]) if fields[5] else 0.0
                        change_amt = float(fields[31]) if len(fields) > 31 and fields[31] else 0.0
                        change_rate = float(fields[32]) if len(fields) > 32 and fields[32] else 0.0
                        high_price = float(fields[33]) if len(fields) > 33 and fields[33] else 0.0
                        low_price = float(fields[34]) if len(fields) > 34 and fields[34] else 0.0
                        quote_time = fields[30] if len(fields) > 30 else ""

                        if current_price == 0.0 and last_close > 0.0:
                            current_price = last_close

                        sec_type = fields[61] if len(fields) > 61 else ""
                        is_etf = ("ETF" in name) or (sec_type == "ETF") or code.startswith(("51", "15", "56", "58", "16"))
                        iopv = float(fields[78]) if len(fields) > 78 and fields[78] else 0.0
                        premium_rate = float(fields[77]) if len(fields) > 77 and fields[77] else 0.0

                        results[original_code] = {
                            "code": code,
                            "name": name,
                            "current_price": current_price,
                            "last_close_price": last_close,
                            "open_price": open_price,
                            "change_amount": change_amt,
                            "change_rate": change_rate,
                            "high_price": high_price,
                            "low_price": low_price,
                            "quote_time": quote_time,
                            "is_valuation": False,
                            "asset_type": "stock",
                            "is_etf": is_etf,
                            "iopv": iopv,
                            "premium_rate": premium_rate
                        }
        except Exception as e:
            print(f"[QuoteService] get_stock_quotes error: {e}")

        return results

    async def get_fund_quotes(self, codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取场外基金实时盘中估值及最新净值
        先通过新浪接口批量拉取 fu_ (盘中实时估值)
        对于未覆盖的，回退到 f_ (官方净值) 或蛋卷基金接口
        """
        if not codes:
            return {}

        results = {}
        # 批量获取新浪实时估值 fu_{code}
        query_fu = ",".join([f"fu_{c}" for c in codes])
        url_fu = f"http://hq.sinajs.cn/list={query_fu}"

        try:
            async with httpx.AsyncClient(headers=self.sina_headers, timeout=6.0) as client:
                resp = await client.get(url_fu)
                text = resp.content.decode("gbk", errors="ignore")

                for line in text.split(";"):
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    left, right = line.split("=", 1)
                    code = left.replace("var hq_str_fu_", "").strip()
                    content = right.strip('"\r\n ')
                    if not content:
                        continue
                    fields = content.split(",")
                    # fields: [name, time, gsz, dwjz, ljjz, ?, gszzl, date, ...]
                    if len(fields) >= 7:
                        name = fields[0]
                        quote_time = f"{fields[7]} {fields[1]}" if len(fields) > 7 else fields[1]
                        current_price = float(fields[2]) if fields[2] else 0.0
                        last_close = float(fields[3]) if fields[3] else 0.0
                        change_rate = float(fields[6]) if fields[6] else 0.0
                        change_amt = round(current_price - last_close, 4)

                        results[code] = {
                            "code": code,
                            "name": name,
                            "current_price": current_price,
                            "last_close_price": last_close,
                            "change_amount": change_amt,
                            "change_rate": change_rate,
                            "quote_time": quote_time,
                            "is_valuation": True,
                            "asset_type": "fund"
                        }
        except Exception as e:
            print(f"[QuoteService] get_fund_quotes error: {e}")

        # 对于没有取到估值的基金，拉取官方公布净值 f_{code}
        missing_codes = [c for c in codes if c not in results or results[c]["current_price"] == 0.0]
        if missing_codes:
            query_f = ",".join([f"f_{c}" for c in missing_codes])
            url_f = f"http://hq.sinajs.cn/list={query_f}"
            try:
                async with httpx.AsyncClient(headers=self.sina_headers, timeout=6.0) as client:
                    resp = await client.get(url_f)
                    text = resp.content.decode("gbk", errors="ignore")
                    for line in text.split(";"):
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        left, right = line.split("=", 1)
                        code = left.replace("var hq_str_f_", "").strip()
                        content = right.strip('"\r\n ')
                        if not content:
                            continue
                        fields = content.split(",")
                        # fields: [name, dwjz, ljjz, last_dwjz, date, fund_scale]
                        if len(fields) >= 5:
                            name = fields[0]
                            current_price = float(fields[1]) if fields[1] else 0.0
                            last_close = float(fields[3]) if fields[3] else current_price
                            quote_date = fields[4]
                            change_amt = round(current_price - last_close, 4)
                            change_rate = round((change_amt / last_close) * 100, 2) if last_close > 0 else 0.0

                            results[code] = {
                                "code": code,
                                "name": name,
                                "current_price": current_price,
                                "last_close_price": last_close,
                                "change_amount": change_amt,
                                "change_rate": change_rate,
                                "quote_time": quote_date,
                                "is_valuation": False,
                                "asset_type": "fund"
                            }
            except Exception as e:
                print(f"[QuoteService] missing_codes f_ error: {e}")

        return results

    async def get_multi_quotes(self, items: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        根据标的列表自动分流股票与基金，并发聚合行情
        items: [{"code": "600519", "asset_type": "stock"}, {"code": "161725", "asset_type": "fund"}]
        """
        stock_codes = []
        fund_codes = []

        for item in items:
            code = str(item.get("code", "")).strip()
            asset_type = item.get("asset_type", "stock")
            if asset_type == "fund":
                fund_codes.append(code)
            else:
                stock_codes.append(code)

        results = {}
        if stock_codes:
            stock_res = await self.get_stock_quotes(stock_codes)
            results.update(stock_res)

        if fund_codes:
            fund_res = await self.get_fund_quotes(fund_codes)
            results.update(fund_res)

        return results

    async def search_symbol(self, keyword: str) -> List[Dict[str, Any]]:
        """模糊搜索标的（A股、ETF、场外基金）"""
        keyword = keyword.strip()
        if not keyword:
            return []

        url = f"https://searchapi.eastmoney.com/api/suggest/get?type=14&token=4f22e26c03c09e1f3e9f416a233e590f&input={keyword}"
        candidates = []
        try:
            async with httpx.AsyncClient(headers=self.qq_headers, timeout=5.0) as client:
                resp = await client.get(url)
                data = resp.json()
                items = data.get("QuotationCodeTable", {}).get("Data", []) or []
                for it in items:
                    code = it.get("Code", "")
                    name = it.get("Name", "")
                    classify = it.get("Classify", "")
                    security_type = it.get("SecurityTypeName", "")

                    asset_type = "fund" if ("基金" in security_type or classify == "Fund") else "stock"
                    candidates.append({
                        "code": code,
                        "name": name,
                        "asset_type": asset_type,
                        "classify": classify,
                        "security_type": security_type
                    })
        except Exception as e:
            print(f"[QuoteService] search_symbol error: {e}")

        return candidates

quote_service = QuoteService()
