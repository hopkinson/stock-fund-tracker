import re
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.database import Position, Account
from app.services.quote_service import quote_service

# ponytail: minimal direct sync without heavy headless browsers
class AutoSyncEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Accept": "application/json, text/plain, */*"
        }

    async def sync_tiantian_assets(self, account: Account, db: Session) -> Dict[str, Any]:
        """天天基金移动端持仓直接同步"""
        cookie = (account.cookie or "").strip().strip('"').strip("'")
        if not cookie:
            return {"success": False, "message": "未绑定天天基金凭证"}

        url = "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNUserAsset"
        headers = {
            **self.headers,
            "Cookie": cookie,
            "Referer": "https://tradeh5.1234567.com.cn/"
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
                resp = await client.post(url, data={"deviceid": "PortfolioHub", "version": "6.6.0"})
                if resp.status_code in (301, 302) or "<html" in resp.text.lower()[:100]:
                    return {"success": False, "message": "天天基金登录已过期，请在网页重新登录并复制 Cookie"}
                try:
                    data = resp.json()
                except Exception:
                    return {"success": False, "message": "天天基金凭证无效或返回异常，请重新复制 Cookie"}
                
                # ponytail: check auth failure
                if data.get("ErrCode") != 0 and not data.get("Success", True):
                    return {"success": False, "message": f"天天基金会话已过期: {data.get('ErrMsg', '请重新绑定')}"}

                items = data.get("Datas") or data.get("Data") or data.get("data") or []
                if isinstance(items, dict):
                    items = items.get("list") or items.get("items") or items.get("Datas") or []
                count = 0
                for item in items:
                    code = str(item.get("FCODE") or item.get("fund_code") or "").strip()
                    name = item.get("SHORTNAME") or item.get("fund_name") or f"基金{code}"
                    shares = float(item.get("VOL") or item.get("shares") or 0.0)
                    cost = float(item.get("COST") or item.get("cost_price") or 0.0)
                    if not code or shares <= 0:
                        continue

                    pos = db.query(Position).filter(Position.account_id == account.id, Position.code == code).first()
                    if pos:
                        pos.shares = shares
                        if cost > 0: pos.cost_price = cost
                        pos.name = name
                    else:
                        db.add(Position(
                            account_id=account.id,
                            platform="tiantian",
                            asset_type="fund",
                            code=code,
                            name=name,
                            shares=shares,
                            cost_price=cost,
                            notes="天天基金自动同步"
                        ))
                    count += 1
                db.commit()
                return {"success": True, "message": f"天天基金同步成功，更新 {count} 只基金"}
        except Exception as e:
            return {"success": False, "message": f"同步异常: {str(e)}"}

    async def sync_xueqiu_portfolio(self, account: Account, db: Session) -> Dict[str, Any]:
        """雪球/蛋卷真实持仓与组合自动同步"""
        cookie = (account.cookie or "").strip().strip('"').strip("'")
        if not cookie:
            return {"success": False, "message": "未绑定雪球凭证"}

        headers = {
            **self.headers,
            "Cookie": cookie if "xq_a_token" in cookie else f"xq_a_token={cookie}",
            "Referer": "https://xueqiu.com"
        }

        # 优先读取雪球持仓组合接口 category=2 (持仓)
        url = "https://stock.xueqiu.com/v5/stock/portfolio/stock/list.json?category=2&size=100"
        try:
            async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code in (400, 401):
                    return {"success": False, "message": "雪球凭据已失效，请重新绑定"}

                try:
                    res = resp.json()
                except Exception:
                    return {"success": False, "message": "雪球接口返回非有效JSON，凭证可能已过期"}

                stocks = res.get("data", {}).get("stocks", [])
                count = 0
                for item in stocks:
                    raw_symbol = item.get("symbol", "")
                    name = item.get("name", "")
                    code = re.sub(r"^[A-Za-z]+", "", raw_symbol)
                    shares = float(item.get("shares") or item.get("holding_amount") or 0.0)
                    cost = float(item.get("cost_price") or 0.0)
                    if not code: continue

                    is_fund = "基金" in name or code.startswith(("15", "16", "51", "58"))
                    pos = db.query(Position).filter(Position.account_id == account.id, Position.code == code).first()
                    if pos:
                        if shares > 0: pos.shares = shares
                        if cost > 0: pos.cost_price = cost
                        pos.name = name
                    else:
                        db.add(Position(
                            account_id=account.id,
                            platform="xueqiu",
                            asset_type="fund" if is_fund else "stock",
                            code=code,
                            name=name,
                            shares=shares,
                            cost_price=cost,
                            notes="雪球自动同步"
                        ))
                    count += 1
                db.commit()
                return {"success": True, "message": f"雪球持仓同步成功，共更新 {count} 个标的"}
        except Exception as e:
            return {"success": False, "message": f"雪球同步异常: {str(e)}"}

    async def sync_eastmoney_web(self, account: Account, db: Session) -> Dict[str, Any]:
        """东方财富 Web 交易持仓自动同步 (jywg.18.cn)"""
        raw_input = (account.cookie or "").strip()
        if not raw_input:
            return {"success": False, "message": "未绑定东方财富交易凭据"}

        # 1. 智能兼容：如果用户粘贴的是整个 fetch 语句或包含 validatekey 的 URL
        validatekey = None
        vk_match = re.search(r"validatekey=([a-zA-Z0-9_-]+)", raw_input)
        if vk_match:
            validatekey = vk_match.group(1)

        # 2. 提取真正的 Cookie
        cookie_match = re.search(r'["\']?cookie["\']?\s*[:=]\s*["\']?([^"\'\r\n]+)', raw_input, re.I)
        cookie = cookie_match.group(1).strip() if cookie_match else raw_input.strip().strip('"\'')

        # 3. 校验东财交易会话的关键凭据
        if "Uid" not in cookie and "eastmoney_txzq_zjzh" not in cookie and "st_si" not in cookie:
            return {
                "success": False,
                "message": "Cookie中缺少东财交易会话凭据（如 Uid / eastmoney_txzq_zjzh），请确认已登录网页端后复制完整 Cookie。"
            }

        # 4. 请求真正的持仓与资产数据接口
        url = "https://jywg.18.cn/Com/queryAssetAndPositionV1"
        params = {}
        if validatekey:
            params["validatekey"] = validatekey

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Cookie": cookie,
            "Referer": "https://jywg.18.cn/Search/Position",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        post_data = {
            "moneyType": "RMB",
            "qqhs": "999999",
            "dwc": ""
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
                resp = await client.post(url, params=params, data=post_data)
                if resp.status_code in (301, 302) or "login" in str(resp.url).lower():
                    return {"success": False, "message": "东财登录已过期或未登录，请在东财交易端登录后重新复制 Cookie"}

                if "<html" in resp.text.lower()[:100]:
                    return {"success": False, "message": "东财交易会话已失效（返回登录页面），请重新登录网页复制 Cookie"}

                if not resp.text.strip():
                    return {"success": False, "message": "东财接口返回空响应，请确认交易端是否在线并重新复制 Cookie"}

                try:
                    data = resp.json()
                except Exception:
                    return {"success": False, "message": "东财接口返回非有效 JSON，会话可能已过期，请重新登录"}

                status = str(data.get("Status", ""))
                if status not in ("0", "200"):
                    err_msg = data.get("Message") or "交易会话已超时或失效"
                    return {"success": False, "message": f"东财交易同步失败: {err_msg}，请重新登录网页并更新 Cookie"}

                items = data.get("Data", []) or []
                if isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
                    asset_info = items[0]
                    positions = asset_info.get("positions", []) or []
                    bonds = asset_info.get("bonds", []) or []
                    all_positions = positions + bonds
                else:
                    all_positions = []

                if not all_positions:
                    return {"success": True, "message": "东方财富同步成功，当前账户无持仓标的"}

                count = 0
                synced_codes = set()
                for p in all_positions:
                    code = str(p.get("Zqdm") or p.get("zq_code") or "").strip()
                    name = p.get("Zqmc") or p.get("zq_name") or f"证券{code}"
                    shares = float(p.get("Zqsl") or p.get("current_amount") or 0.0)
                    cost = float(p.get("Cbjg") or p.get("Ckcbj") or p.get("cost_price") or 0.0)
                    if not code or shares <= 0:
                        continue

                    synced_codes.add(code)
                    is_fund = "基金" in name or "ETF" in name or code.startswith(("15", "16", "51", "56", "58"))
                    pos = db.query(Position).filter(Position.account_id == account.id, Position.code == code).first()
                    if pos:
                        pos.shares = shares
                        if cost > 0: pos.cost_price = cost
                        pos.name = name
                        pos.asset_type = "fund" if is_fund else "stock"
                    else:
                        db.add(Position(
                            account_id=account.id,
                            platform="eastmoney",
                            asset_type="fund" if is_fund else "stock",
                            code=code,
                            name=name,
                            shares=shares,
                            cost_price=cost,
                            notes="东财实盘自动同步"
                        ))
                    count += 1

                # 清理已不在实际持仓中的旧标的（如历史模拟数据或已清仓标的）
                old_positions = db.query(Position).filter(Position.account_id == account.id).all()
                for op in old_positions:
                    if op.code not in synced_codes:
                        db.delete(op)

                db.commit()
                return {"success": True, "message": f"东方财富实盘同步成功，更新 {count} 只证券持仓"}
        except Exception as e:
            return {"success": False, "message": f"东财交易同步异常: {str(e)}"}

    async def sync_yangjibao(self, account: Account, db: Session) -> Dict[str, Any]:
        """
        养基宝持仓同步
        支持两种模式：
        1. 凭证/Token 模式：配置养基宝小程序/App的 Authorization Token 或接口 URL 自动拉取
        2. 文本/JSON 直接粘贴模式：将小程序抓包或导出的 JSON/文本直接存入凭证中，自动智能提取基金代码、份额和成本
        """
        credential = (account.cookie or "").strip()
        if not credential:
            return {"success": False, "message": "未配置养基宝凭据或持仓数据"}

        # 模式 A: 如果是 JSON 数据或包含持仓数组，直接智能解析
        if credential.startswith(("[", "{")) or "code" in credential or "fund" in credential:
            try:
                # 尝试直接解析 JSON
                data = json.loads(credential)
                items = data if isinstance(data, list) else data.get("data", []) or data.get("list", []) or data.get("positions", [])
                if items:
                    count = 0
                    for item in items:
                        code = str(item.get("code") or item.get("fundCode") or item.get("FCODE") or item.get("fund_code") or "").strip()
                        name = item.get("name") or item.get("fundName") or item.get("SHORTNAME") or f"基金{code}"
                        shares = float(item.get("shares") or item.get("vol") or item.get("amount") or item.get("holding") or 0.0)
                        cost = float(item.get("cost") or item.get("costPrice") or item.get("nav") or 0.0)
                        if not code: continue

                        pos = db.query(Position).filter(Position.account_id == account.id, Position.code == code).first()
                        if pos:
                            if shares > 0: pos.shares = shares
                            if cost > 0: pos.cost_price = cost
                            pos.name = name
                        else:
                            db.add(Position(
                                account_id=account.id,
                                platform="yangjibao",
                                asset_type="fund",
                                code=code,
                                name=name,
                                shares=shares,
                                cost_price=cost,
                                notes="养基宝同步导入"
                            ))
                        count += 1
                    db.commit()
                    return {"success": True, "message": f"养基宝持仓数据解析成功，共更新 {count} 只基金"}
            except Exception:
                pass

        # 模式 B: Token / HTTP 请求模式 (如果输入的是 URL 或携带 Bearer Token)
        # 支持用户输入: url|token 形式或直接 token
        url = "https://api.yangjibao.com/user/fund/positions" # 默认或由配置传入
        token = credential
        if "http://" in credential or "https://" in credential:
            parts = credential.split("|")
            url = parts[0].strip()
            token = parts[1].strip() if len(parts) > 1 else ""

        headers = {
            **self.headers,
            "Authorization": token if token.startswith("Bearer ") else f"Bearer {token}",
            "token": token
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", []) or data.get("list", []) or []
                    count = 0
                    for item in items:
                        code = str(item.get("code") or item.get("fundCode") or "").strip()
                        name = item.get("name") or item.get("fundName") or f"基金{code}"
                        shares = float(item.get("shares") or item.get("amount") or 0.0)
                        cost = float(item.get("cost") or item.get("costPrice") or 0.0)
                        if not code: continue

                        pos = db.query(Position).filter(Position.account_id == account.id, Position.code == code).first()
                        if pos:
                            if shares > 0: pos.shares = shares
                            if cost > 0: pos.cost_price = cost
                            pos.name = name
                        else:
                            db.add(Position(
                                account_id=account.id,
                                platform="yangjibao",
                                asset_type="fund",
                                code=code,
                                name=name,
                                shares=shares,
                                cost_price=cost,
                                notes="养基宝自动同步"
                            ))
                        count += 1
                    db.commit()
                    return {"success": True, "message": f"养基宝接口同步成功，共更新 {count} 只基金"}
                else:
                    return {"success": False, "message": f"养基宝接口请求失败 ({resp.status_code})，请检查 Token"}
        except Exception as e:
            return {"success": False, "message": f"养基宝同步异常: {str(e)}"}

auto_sync_engine = AutoSyncEngine()

