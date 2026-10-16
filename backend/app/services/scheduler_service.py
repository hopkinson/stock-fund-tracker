from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.models.database import SessionLocal
from app.services.portfolio_service import portfolio_service
from app.services.notify_service import notify_service

scheduler = AsyncIOScheduler()

def is_trading_time() -> bool:
    """判断当前是否为 A股 交易时间 (周一到周五 09:15-11:35, 12:55-15:05)"""
    now = datetime.now()
    if now.weekday() >= 5:  # 周六周日
        return False
    current_time = now.strftime("%H:%M")
    if ("09:15" <= current_time <= "11:35") or ("12:55" <= current_time <= "15:05"):
        return True
    return False

from app.models.database import Account
from app.services.auto_sync_engine import auto_sync_engine

async def job_market_refresh():
    """盘中定时刷新行情与触发异动检查"""
    if is_trading_time():
        db = SessionLocal()
        try:
            await portfolio_service.refresh_all_positions(db)
            # ponytail: sync enabled accounts every 10 mins during trading
            now = datetime.now()
            if now.minute % 10 == 0 and now.second < 25:
                accounts = db.query(Account).filter(Account.auto_sync == True).all()
                for acc in accounts:
                    if acc.platform == "xueqiu":
                        await auto_sync_engine.sync_xueqiu_portfolio(acc, db)
                    elif acc.platform == "tiantian":
                        await auto_sync_engine.sync_tiantian_assets(acc, db)
                    elif acc.platform == "eastmoney":
                        await auto_sync_engine.sync_eastmoney_web(acc, db)
                    elif acc.platform == "yangjibao":
                        await auto_sync_engine.sync_yangjibao(acc, db)
        finally:
            db.close()



async def job_open_market_notify():
    """09:25 开盘前提醒"""
    now = datetime.now()
    if now.weekday() >= 5:
        return
    db = SessionLocal()
    try:
        report = await portfolio_service.get_summary_report(db, "🔔 A股开盘集合竞价提醒")
        await notify_service.send_notification("🔔 A股开盘提醒", report, db, event_type="open")
    finally:
        db.close()

async def job_close_market_notify():
    """15:05 收盘战报与记录快照"""
    now = datetime.now()
    if now.weekday() >= 5:
        return
    db = SessionLocal()
    try:
        # 先记录快照
        portfolio_service.record_daily_snapshot(db)
        report = await portfolio_service.get_summary_report(db, "🏁 今日A股收盘战报")
        await notify_service.send_notification("🏁 今日收盘战报", report, db, event_type="close")
    finally:
        db.close()

async def job_night_fund_notify():
    """21:45 场外基金最终公布净值刷新与报告"""
    now = datetime.now()
    if now.weekday() >= 5:
        return
    db = SessionLocal()
    try:
        # 刷新官方已公布净值
        portfolio_service.record_daily_snapshot(db)
        report = await portfolio_service.get_summary_report(db, "🌙 今日基金官方净值核算报告")
        await notify_service.send_notification("🌙 基金净值更新报告", report, db, event_type="night_fund")
    finally:
        db.close()

def start_scheduler():
    # 盘中每 20 秒刷新一次
    scheduler.add_job(job_market_refresh, IntervalTrigger(seconds=20), id="market_refresh", replace_existing=True)
    
    # 09:25 开盘
    scheduler.add_job(job_open_market_notify, CronTrigger(hour=9, minute=25, day_of_week="mon-fri"), id="open_notify", replace_existing=True)
    
    # 15:05 收盘
    scheduler.add_job(job_close_market_notify, CronTrigger(hour=15, minute=5, day_of_week="mon-fri"), id="close_notify", replace_existing=True)
    
    # 21:45 夜间净值更新
    scheduler.add_job(job_night_fund_notify, CronTrigger(hour=21, minute=45, day_of_week="mon-fri"), id="night_fund_notify", replace_existing=True)

    scheduler.start()
    print("[Scheduler] 定时调度服务已成功启动")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("[Scheduler] 定时调度服务已停止")
