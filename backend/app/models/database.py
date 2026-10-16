from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 账户名称，如"我的雪球"、"东财主账户"
    platform = Column(String(30), nullable=False)  # xueqiu, tiantian, eastmoney, manual
    cookie = Column(Text, nullable=True)  # 用于自动同步的 Cookie / Token
    auto_sync = Column(Boolean, default=False)  # 是否开启定时自动同步
    last_sync_time = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="ready")  # ready, syncing, success, error
    sync_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    platform = Column(String(30), default="manual")  # xueqiu, tiantian, eastmoney, manual
    asset_type = Column(String(20), default="stock")  # stock(股票/场内ETF), fund(场外公募基金)
    code = Column(String(20), index=True, nullable=False)  # 如 600519, 000001, 161725
    name = Column(String(100), nullable=False)  # 贵州茅台 / 招商中证白酒
    
    shares = Column(Float, default=0.0)  # 持有份额 / 股数
    cost_price = Column(Float, default=0.0)  # 持仓成本价
    
    # 动态行情字段
    current_price = Column(Float, default=0.0)  # 当前价格 / 盘中估算净值
    last_close_price = Column(Float, default=0.0)  # 昨收价 / 昨日官方净值
    market_value = Column(Float, default=0.0)  # 当前市值
    total_cost = Column(Float, default=0.0)  # 持仓总成本
    
    today_profit = Column(Float, default=0.0)  # 今日预估盈亏金额
    today_profit_rate = Column(Float, default=0.0)  # 今日涨跌幅 %
    total_profit = Column(Float, default=0.0)  # 累计总盈亏金额
    total_profit_rate = Column(Float, default=0.0)  # 累计收益率 %
    
    is_valuation = Column(Boolean, default=False)  # 是否为盘中实时估值(对于场外基金)
    quote_time = Column(String(50), nullable=True)  # 行情最后更新时间戳
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    account = relationship("Account", back_populates="positions")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False)  # 标的代码
    name = Column(String(100), nullable=False)
    rule_type = Column(String(30), nullable=False)  
    # 规则: day_change_above (日涨超), day_change_below (日跌超), stop_profit (止盈), stop_loss (止损)
    threshold = Column(Float, nullable=False)  # 百分比(%)或目标价格
    enabled = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(30), unique=True, nullable=False)  # pushplus
    name = Column(String(50), nullable=False)
    webhook_url = Column(Text, nullable=True)
    secret = Column(String(100), nullable=True)
    token = Column(String(100), nullable=True)  # PushPlus token
    enabled = Column(Boolean, default=False)
    notify_on_open = Column(Boolean, default=True)  # 9:25 开盘提醒
    notify_on_close = Column(Boolean, default=True)  # 15:05 收盘战报
    notify_on_alert = Column(Boolean, default=True)  # 实时异动报警
    notify_on_night_fund = Column(Boolean, default=True)  # 晚上基金净值更新报告


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    total_asset = Column(Float, default=0.0)  # 总资产
    total_cost = Column(Float, default=0.0)  # 总成本
    today_profit = Column(Float, default=0.0)  # 当日盈亏金额
    today_profit_rate = Column(Float, default=0.0)  # 当日收益率
    total_profit = Column(Float, default=0.0)  # 累计总盈亏
    total_profit_rate = Column(Float, default=0.0)  # 累计总收益率
    created_at = Column(DateTime, default=datetime.now)


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # 初始化默认账户如果不存在
    if not db.query(Account).first():
        default_accounts = [
            Account(name="东方财富A股", platform="eastmoney", auto_sync=False),
            Account(name="天天基金", platform="tiantian", auto_sync=False),
            Account(name="雪球基金/投资", platform="xueqiu", auto_sync=False),
            Account(name="养基宝", platform="yangjibao", auto_sync=False),
        ]
        db.add_all(default_accounts)
        db.commit()
    else:
        # 补充养基宝账户
        if not db.query(Account).filter(Account.platform == "yangjibao").first():
            db.add(Account(name="养基宝", platform="yangjibao", auto_sync=False))
            db.commit()


    # 清理非 pushplus 的历史旧渠道配置，只保留 pushplus
    db.query(NotificationConfig).filter(NotificationConfig.channel != "pushplus").delete()
    if not db.query(NotificationConfig).filter(NotificationConfig.channel == "pushplus").first():
        db.add(NotificationConfig(channel="pushplus", name="微信PushPlus推送", enabled=False))
    db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
