from app.models.database import SessionLocal, Position, Account, init_db, AlertRule
from app.services.quote_service import quote_service
import asyncio

async def seed():
    init_db()
    db = SessionLocal()
    
    if db.query(Position).count() == 0:
        print("添加演示初始持仓 (东方财富、天天基金、雪球基金)...")
        em_acc = db.query(Account).filter(Account.platform == "eastmoney").first()
        tt_acc = db.query(Account).filter(Account.platform == "tiantian").first()
        xq_acc = db.query(Account).filter(Account.platform == "xueqiu").first()

        sample_positions = [
            Position(
                account_id=em_acc.id if em_acc else 1,
                platform="eastmoney",
                asset_type="stock",
                code="600519",
                name="贵州茅台",
                shares=200,
                cost_price=1250.0,
                notes="东财A股核心资产"
            ),
            Position(
                account_id=em_acc.id if em_acc else 1,
                platform="eastmoney",
                asset_type="stock",
                code="000001",
                name="平安银行",
                shares=3000,
                cost_price=11.20,
                notes="银行高股息稳健配置"
            ),
            Position(
                account_id=tt_acc.id if tt_acc else 2,
                platform="tiantian",
                asset_type="fund",
                code="161725",
                name="招商中证白酒指数(LOF)A",
                shares=10000,
                cost_price=0.5500,
                notes="天天基金定投"
            ),
            Position(
                account_id=xq_acc.id if xq_acc else 3,
                platform="xueqiu",
                asset_type="fund",
                code="005827",
                name="易方达蓝筹精选混合",
                shares=8000,
                cost_price=1.6500,
                notes="雪球蛋卷定投组合"
            ),
        ]
        db.add_all(sample_positions)
        db.commit()

        # 添加预警示范
        sample_alerts = [
            AlertRule(code="600519", name="贵州茅台", rule_type="day_change_above", threshold=3.0),
            AlertRule(code="600519", name="贵州茅台", rule_type="day_change_below", threshold=3.0),
            AlertRule(code="161725", name="招商中证白酒指数", rule_type="stop_profit", threshold=20.0),
        ]
        db.add_all(sample_alerts)
        db.commit()
        print("初始演示持仓与预警添加成功！")
    else:
        print("已有持仓数据，跳过初始化。")

    db.close()

if __name__ == "__main__":
    asyncio.run(seed())
