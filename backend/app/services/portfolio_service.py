from datetime import datetime, date
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.models.database import Position, AlertRule, DailySnapshot
from app.services.quote_service import quote_service
from app.services.notify_service import notify_service

class PortfolioService:
    async def refresh_all_positions(self, db: Session) -> Dict[str, Any]:
        """
        全量刷新所有持仓标的的最新行情，并重新核算盈亏
        """
        positions = db.query(Position).all()
        if not positions:
            return {
                "total_asset": 0.0,
                "total_cost": 0.0,
                "today_profit": 0.0,
                "today_profit_rate": 0.0,
                "total_profit": 0.0,
                "total_profit_rate": 0.0,
                "positions": []
            }

        items = [{"code": pos.code, "asset_type": pos.asset_type} for pos in positions]
        quotes = await quote_service.get_multi_quotes(items)

        total_asset = 0.0
        total_cost = 0.0
        today_profit = 0.0
        alerts_triggered = []

        # 获取启用的预警规则
        rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
        rules_by_code: Dict[str, List[AlertRule]] = {}
        for r in rules:
            rules_by_code.setdefault(r.code, []).append(r)

        for pos in positions:
            q = quotes.get(pos.code)
            if q:
                if not pos.name or pos.name.startswith("标的"):
                    pos.name = q.get("name", pos.name)
                pos.current_price = q.get("current_price", pos.current_price)
                pos.last_close_price = q.get("last_close_price", pos.last_close_price)
                pos.today_profit_rate = q.get("change_rate", 0.0)
                pos.is_valuation = q.get("is_valuation", False)
                pos.quote_time = q.get("quote_time", "")

            # 计算市值与盈亏
            pos.market_value = round(pos.shares * pos.current_price, 2)
            pos.total_cost = round(pos.shares * pos.cost_price, 2)
            
            # 今日盈亏金额 (当前价 - 昨收价) * 份额
            diff_price = pos.current_price - pos.last_close_price
            pos.today_profit = round(pos.shares * diff_price, 2)
            
            # 累计总盈亏
            pos.total_profit = round(pos.market_value - pos.total_cost, 2)
            if pos.total_cost > 0:
                pos.total_profit_rate = round((pos.total_profit / pos.total_cost) * 100, 2)
            else:
                pos.total_profit_rate = 0.0

            total_asset += pos.market_value
            total_cost += pos.total_cost
            today_profit += pos.today_profit

            # 预警检查
            for rule in rules_by_code.get(pos.code, []):
                triggered = False
                msg = ""
                if rule.rule_type == "day_change_above" and pos.today_profit_rate >= rule.threshold:
                    triggered = True
                    msg = f"📈【涨幅提醒】{pos.name}({pos.code}) 今日上涨达 +{pos.today_profit_rate}% (目标: +{rule.threshold}%)"
                elif rule.rule_type == "day_change_below" and pos.today_profit_rate <= -abs(rule.threshold):
                    triggered = True
                    msg = f"📉【跌幅提醒】{pos.name}({pos.code}) 今日下跌达 {pos.today_profit_rate}% (目标: -{rule.threshold}%)"
                elif rule.rule_type == "stop_profit" and pos.total_profit_rate >= rule.threshold:
                    triggered = True
                    msg = f"🎯【止盈提醒】{pos.name}({pos.code}) 累计收益达 +{pos.total_profit_rate}% (目标: +{rule.threshold}%)"
                elif rule.rule_type == "stop_loss" and pos.total_profit_rate <= -abs(rule.threshold):
                    triggered = True
                    msg = f"⚠️【止损提醒】{pos.name}({pos.code}) 累计亏损达 {pos.total_profit_rate}% (目标: -{rule.threshold}%)"

                if triggered:
                    # 避免一小时内重复触发
                    now = datetime.now()
                    if not rule.last_triggered_at or (now - rule.last_triggered_at).total_seconds() > 3600:
                        rule.last_triggered_at = now
                        alerts_triggered.append(msg)

        db.commit()

        # 如果有预警触发，推送通知
        if alerts_triggered:
            alert_text = "\n\n".join(alerts_triggered)
            await notify_service.send_notification("⚡ 持仓涨跌与止盈提醒", alert_text, db, event_type="alert")

        overall_total_profit = round(total_asset - total_cost, 2)
        overall_total_rate = round((overall_total_profit / total_cost * 100), 2) if total_cost > 0 else 0.0
        yesterday_asset = total_asset - today_profit
        overall_today_rate = round((today_profit / yesterday_asset * 100), 2) if yesterday_asset > 0 else 0.0

        return {
            "total_asset": round(total_asset, 2),
            "total_cost": round(total_cost, 2),
            "today_profit": round(today_profit, 2),
            "today_profit_rate": overall_today_rate,
            "total_profit": overall_total_profit,
            "total_profit_rate": overall_total_rate,
            "position_count": len(positions)
        }

    async def get_summary_report(self, db: Session, title: str) -> str:
        """生成格式美观的 Markdown 资产播报"""
        res = await self.refresh_all_positions(db)
        positions = db.query(Position).all()
        # 按照今日盈亏绝对值排序找出今日最大的贡献/亏损标的
        sorted_pos = sorted(positions, key=lambda p: p.today_profit, reverse=True)

        sign = "+" if res["today_profit"] >= 0 else ""
        text = f"**📊 资产概览：**\n"
        text += f"- **总市值**：¥{res['total_asset']:,.2f}\n"
        text += f"- **总成本**：¥{res['total_cost']:,.2f}\n"
        text += f"- **今日盈亏**：{sign}¥{res['today_profit']:,.2f} ({sign}{res['today_profit_rate']}%)\n"
        text += f"- **累计盈亏**：¥{res['total_profit']:,.2f} ({res['total_profit_rate']}%)\n\n"

        if sorted_pos:
            top_gain = sorted_pos[0]
            top_loss = sorted_pos[-1]
            text += f"**🚀 今日涨幅最大**：{top_gain.name} ({top_gain.today_profit_rate:+.2f}%，盈利 ¥{top_gain.today_profit:+.2f})\n"
            if top_loss.today_profit < 0:
                text += f"**🔻 今日跌幅最大**：{top_loss.name} ({top_loss.today_profit_rate:+.2f}%，亏损 ¥{top_loss.today_profit:+.2f})\n\n"

        text += "**📈 持仓明细一览：**\n"
        for p in sorted_pos:
            p_sign = "+" if p.today_profit >= 0 else ""
            text += f"- {p.name} ({p.code}): 市值 ¥{p.market_value:,.2f} | 今日 {p_sign}{p.today_profit_rate:.2f}% ({p_sign}¥{p.today_profit:.2f})\n"

        return text

    def record_daily_snapshot(self, db: Session):
        """记录每日收盘资产快照"""
        today_str = date.today().strftime("%Y-%m-%d")
        positions = db.query(Position).all()
        total_asset = sum(p.market_value for p in positions)
        total_cost = sum(p.total_cost for p in positions)
        today_profit = sum(p.today_profit for p in positions)
        total_profit = total_asset - total_cost
        total_profit_rate = round((total_profit / total_cost * 100), 2) if total_cost > 0 else 0.0
        yesterday_asset = total_asset - today_profit
        today_profit_rate = round((today_profit / yesterday_asset * 100), 2) if yesterday_asset > 0 else 0.0

        snapshot = db.query(DailySnapshot).filter(DailySnapshot.date == today_str).first()
        if snapshot:
            snapshot.total_asset = round(total_asset, 2)
            snapshot.total_cost = round(total_cost, 2)
            snapshot.today_profit = round(today_profit, 2)
            snapshot.today_profit_rate = today_profit_rate
            snapshot.total_profit = round(total_profit, 2)
            snapshot.total_profit_rate = total_profit_rate
        else:
            snapshot = DailySnapshot(
                date=today_str,
                total_asset=round(total_asset, 2),
                total_cost=round(total_cost, 2),
                today_profit=round(today_profit, 2),
                today_profit_rate=today_profit_rate,
                total_profit=round(total_profit, 2),
                total_profit_rate=total_profit_rate
            )
            db.add(snapshot)
        db.commit()

portfolio_service = PortfolioService()
