from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.models.database import get_db, Position, Account, AlertRule, NotificationConfig, DailySnapshot
from app.services.portfolio_service import portfolio_service
from app.services.notify_service import notify_service
from app.services.auto_sync_engine import auto_sync_engine
from app.services.kol_tracker_service import kol_tracker_service

router = APIRouter()

# ----------- 请求模型 -----------
class AccountUpdate(BaseModel):
    name: Optional[str] = None
    cookie: Optional[str] = None
    auto_sync: Optional[bool] = None

class AlertRuleCreate(BaseModel):
    code: str
    name: str
    rule_type: str  # day_change_above, day_change_below, stop_profit, stop_loss
    threshold: float
    enabled: bool = True

class NotificationConfigUpdate(BaseModel):
    name: Optional[str] = None
    webhook_url: Optional[str] = None
    secret: Optional[str] = None
    token: Optional[str] = None
    enabled: Optional[bool] = None
    notify_on_open: Optional[bool] = None
    notify_on_close: Optional[bool] = None
    notify_on_alert: Optional[bool] = None
    notify_on_night_fund: Optional[bool] = None

# ----------- 资产与持仓接口 -----------

@router.get("/portfolio/summary")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """获取资产统计概览、平台分布、资产类型分布及历史收益曲线"""
    summary = await portfolio_service.refresh_all_positions(db)
    positions = db.query(Position).all()

    # 平台分布
    platform_map = {}
    type_map = {}
    for p in positions:
        platform_name = p.platform or "eastmoney"
        platform_map[platform_name] = platform_map.get(platform_name, 0.0) + p.market_value
        
        type_name = "公募基金" if p.asset_type == "fund" else "股票/ETF"
        type_map[type_name] = type_map.get(type_name, 0.0) + p.market_value

    # 历史快照（最近 30 天）
    snapshots = db.query(DailySnapshot).order_by(DailySnapshot.date.desc()).limit(30).all()
    snapshots.reverse()
    chart_data = [{
        "date": s.date,
        "total_asset": s.total_asset,
        "today_profit": s.today_profit,
        "total_profit": s.total_profit
    } for s in snapshots]

    return {
        "summary": summary,
        "distribution_by_platform": platform_map,
        "distribution_by_type": type_map,
        "history_chart": chart_data
    }

@router.get("/portfolio/positions")
async def list_positions(platform: Optional[str] = None, asset_type: Optional[str] = None, db: Session = Depends(get_db)):
    """获取所有持仓列表，支持按平台/类型筛选"""
    query = db.query(Position)
    if platform and platform != "all":
        query = query.filter(Position.platform == platform)
    if asset_type and asset_type != "all":
        query = query.filter(Position.asset_type == asset_type)

    positions = query.order_by(Position.market_value.desc()).all()
    return positions

@router.delete("/portfolio/positions/{pos_id}")
async def delete_position(pos_id: int, db: Session = Depends(get_db)):
    """删除单条持仓记录"""
    pos = db.query(Position).filter(Position.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="持仓不存在")
    db.delete(pos)
    db.commit()
    return {"success": True, "message": "删除成功"}

@router.post("/portfolio/positions/clear")
async def clear_positions(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """清空指定账户或所有持仓"""
    query = db.query(Position)
    if account_id:
        query = query.filter(Position.account_id == account_id)
    count = query.delete()
    db.commit()
    await portfolio_service.refresh_all_positions(db)
    return {"success": True, "message": f"已清空 {count} 条持仓"}

@router.post("/portfolio/refresh")
async def manual_refresh(db: Session = Depends(get_db)):
    """一键立即拉取最新实时行情"""
    summary = await portfolio_service.refresh_all_positions(db)
    return {"success": True, "summary": summary}

# ----------- 账户与自动同步接口 -----------

@router.get("/accounts")
async def list_accounts(db: Session = Depends(get_db)):
    """获取三大平台账户状态"""
    accounts = db.query(Account).filter(Account.platform != "manual").all()
    res = []
    for acc in accounts:
        positions = db.query(Position).filter(Position.account_id == acc.id).all()
        mv = sum(p.market_value for p in positions)
        res.append({
            "id": acc.id,
            "name": acc.name,
            "platform": acc.platform,
            "auto_sync": acc.auto_sync,
            "has_cookie": bool(acc.cookie),
            "last_sync_time": acc.last_sync_time,
            "sync_status": acc.sync_status,
            "sync_message": acc.sync_message,
            "position_count": len(positions),
            "market_value": round(mv, 2)
        })
    return res

@router.put("/accounts/{account_id}")
async def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    if data.name is not None:
        acc.name = data.name
    if data.cookie is not None:
        acc.cookie = data.cookie
    if data.auto_sync is not None:
        acc.auto_sync = data.auto_sync
    db.commit()
    return {"success": True, "message": "账户设置已更新"}

@router.post("/accounts/{account_id}/sync")
async def trigger_account_sync(account_id: int, db: Session = Depends(get_db)):
    """触发指定账户的实时在线持仓自动同步"""
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")

    acc.sync_status = "syncing"
    db.commit()

    if acc.platform == "xueqiu":
        result = await auto_sync_engine.sync_xueqiu_portfolio(acc, db)
    elif acc.platform == "tiantian":
        result = await auto_sync_engine.sync_tiantian_assets(acc, db)
    elif acc.platform == "eastmoney":
        result = await auto_sync_engine.sync_eastmoney_web(acc, db)
    elif acc.platform == "yangjibao":
        result = await auto_sync_engine.sync_yangjibao(acc, db)
    else:
        result = {"success": False, "message": "未知平台"}

    acc.sync_status = "success" if result.get("success") else "error"
    acc.sync_message = result.get("message")
    acc.last_sync_time = datetime.now()
    db.commit()

    if result.get("success"):
        await portfolio_service.refresh_all_positions(db)

    return result

@router.post("/accounts/sync-all")
async def sync_all_accounts(db: Session = Depends(get_db)):
    """一键同步所有已配置凭证的账户"""
    accounts = db.query(Account).filter(Account.platform != "manual").all()
    results = []
    for acc in accounts:
        if not acc.cookie:
            continue
        if acc.platform == "xueqiu":
            res = await auto_sync_engine.sync_xueqiu_portfolio(acc, db)
        elif acc.platform == "tiantian":
            res = await auto_sync_engine.sync_tiantian_assets(acc, db)
        elif acc.platform == "eastmoney":
            res = await auto_sync_engine.sync_eastmoney_web(acc, db)
        elif acc.platform == "yangjibao":
            res = await auto_sync_engine.sync_yangjibao(acc, db)
        else:
            continue
        acc.sync_status = "success" if res.get("success") else "error"
        acc.sync_message = res.get("message")
        acc.last_sync_time = datetime.now()
        results.append({"platform": acc.platform, "result": res})
    
    db.commit()
    await portfolio_service.refresh_all_positions(db)
    return {"success": True, "details": results}


# ----------- 预警规则接口 -----------

@router.get("/alerts")
async def list_alert_rules(db: Session = Depends(get_db)):
    rules = db.query(AlertRule).all()
    return rules

@router.post("/alerts")
async def create_alert_rule(rule_in: AlertRuleCreate, db: Session = Depends(get_db)):
    rule = AlertRule(
        code=rule_in.code,
        name=rule_in.name,
        rule_type=rule_in.rule_type,
        threshold=rule_in.threshold,
        enabled=rule_in.enabled
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/alerts/{rule_id}")
async def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"success": True, "message": "预警规则已删除"}

# ----------- 通知配置接口 -----------

@router.get("/notifications")
async def list_notifications(db: Session = Depends(get_db)):
    configs = db.query(NotificationConfig).filter(NotificationConfig.channel == "pushplus").all()
    return configs

@router.put("/notifications/{channel}")
async def update_notification(channel: str, data: NotificationConfigUpdate, db: Session = Depends(get_db)):
    cfg = db.query(NotificationConfig).filter(NotificationConfig.channel == channel).first()
    if not cfg:
        cfg = NotificationConfig(channel=channel, name=data.name or channel)
        db.add(cfg)

    if data.name is not None:
        cfg.name = data.name
    if data.webhook_url is not None:
        cfg.webhook_url = data.webhook_url
    if data.secret is not None:
        cfg.secret = data.secret
    if data.token is not None:
        cfg.token = data.token
    if data.enabled is not None:
        cfg.enabled = data.enabled
    if data.notify_on_open is not None:
        cfg.notify_on_open = data.notify_on_open
    if data.notify_on_close is not None:
        cfg.notify_on_close = data.notify_on_close
    if data.notify_on_alert is not None:
        cfg.notify_on_alert = data.notify_on_alert
    if data.notify_on_night_fund is not None:
        cfg.notify_on_night_fund = data.notify_on_night_fund

    db.commit()
    return {"success": True, "message": "通知设置已保存"}

@router.post("/notifications/test")
async def test_notification(channel: Optional[str] = None, db: Session = Depends(get_db)):
    """发送一条测试推送消息"""
    summary_report = await portfolio_service.get_summary_report(db, "📢 PortfolioHub 测试推送")
    results = await notify_service.send_notification("📢 PortfolioHub 连通性测试", summary_report, db, event_type="alert")
    return {"success": True, "results": results}

# ----------- AI 诊断与复盘接口 -----------
from app.services.ai_service import ai_service

class AIConfigRequest(BaseModel):
    api_key: str
    api_base: Optional[str] = "https://api.deepseek.com/v1"
    model: Optional[str] = "deepseek-chat"

class AIReviewRequest(BaseModel):
    prompt: Optional[str] = ""

@router.get("/ai/config")
async def get_ai_config():
    masked = ""
    if ai_service.api_key:
        k = ai_service.api_key
        if len(k) > 10:
            masked = f"{k[:7]}********{k[-4:]}"
        else:
            masked = "******"
    return {
        "has_key": bool(ai_service.api_key),
        "masked_key": masked,
        "api_base": ai_service.api_base,
        "model": ai_service.model
    }

@router.post("/ai/config")
async def set_ai_config(cfg: AIConfigRequest):
    if cfg.api_key and "******" not in cfg.api_key:
        ai_service.api_key = cfg.api_key.strip()
    if cfg.api_base:
        ai_service.api_base = cfg.api_base.strip()
    if cfg.model:
        ai_service.model = cfg.model.strip()

    # 持久化写入 .env
    from pathlib import Path
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"AI_API_KEY={ai_service.api_key}\nAI_API_BASE={ai_service.api_base}\nAI_MODEL={ai_service.model}\n")

    return {"success": True, "message": "AI 配置已更新"}

@router.post("/ai/review")
async def request_ai_review(req: AIReviewRequest, db: Session = Depends(get_db)):
    """调用 AI 大模型对当前持仓进行深度操盘复盘"""
    summary = await portfolio_service.refresh_all_positions(db)
    positions = db.query(Position).all()
    symbols = [{"code": p.code, "asset_type": p.asset_type} for p in positions]
    quotes = await quote_service.get_multi_quotes(symbols) if symbols else {}

    pos_data = [{
        "code": p.code,
        "name": p.name,
        "current_price": p.current_price,
        "today_profit_rate": p.today_profit_rate,
        "today_profit": p.today_profit,
        "total_profit_rate": p.total_profit_rate,
        "market_value": p.market_value,
        "cost_price": p.cost_price,
        "shares": p.shares,
        "is_etf": quotes.get(p.code, {}).get("is_etf", False) or "ETF" in p.name or p.code.startswith(("51", "15", "56", "58", "16")),
        "iopv": quotes.get(p.code, {}).get("iopv", 0.0),
        "premium_rate": quotes.get(p.code, {}).get("premium_rate", 0.0)
    } for p in positions]

    result = await ai_service.analyze_portfolio(pos_data, summary, req.prompt)
    return {"success": True, "analysis": result}

# ----------- KOL 调仓验真与快讯接口 -----------

class KOLAnalyzeRequest(BaseModel):
    content: str
    blogger_name: Optional[str] = "小红书博主"
    push_notify: bool = False

@router.post("/kol/analyze")
async def analyze_kol_post(req: KOLAnalyzeRequest, db: Session = Depends(get_db)):
    """分析博主发布的交易动态，结合行情、估值与快讯进行综合验真"""
    result = await kol_tracker_service.analyze_blogger_post(req.content, req.blogger_name)
    if result.get("success") and req.push_notify and result.get("report_markdown"):
        await kol_tracker_service.push_analysis_to_wechat(result["report_markdown"], db)
    return result

@router.get("/kol/news")
async def get_market_news(keyword: Optional[str] = "", limit: int = 20):
    """获取最新 7x24 宏观与行业财经快讯"""
    news = await kol_tracker_service.get_latest_7x24_news(keyword=keyword, limit=limit)
    return {"success": True, "count": len(news), "news": news}


