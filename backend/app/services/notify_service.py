import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.database import NotificationConfig

class NotifyService:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}

    async def send_notification(self, title: str, content_markdown: str, db: Session, event_type: str = "alert") -> Dict[str, Any]:
        """
        向已启用的 PushPlus 微信通知渠道广播消息
        event_type: 'open' (开盘), 'close' (收盘), 'alert' (异动), 'night_fund' (夜间净值)
        """
        channels = db.query(NotificationConfig).filter(
            NotificationConfig.enabled == True,
            NotificationConfig.channel == "pushplus"
        ).all()
        results = {}

        for ch in channels:
            # 检查事件开关
            if event_type == "open" and not ch.notify_on_open:
                continue
            if event_type == "close" and not ch.notify_on_close:
                continue
            if event_type == "alert" and not ch.notify_on_alert:
                continue
            if event_type == "night_fund" and not ch.notify_on_night_fund:
                continue

            try:
                if ch.token:
                    res = await self._send_pushplus(ch.token, title, content_markdown)
                else:
                    res = {"success": False, "message": "未配置 PushPlus Token"}
                results[ch.channel] = res
            except Exception as e:
                results[ch.channel] = {"success": False, "error": str(e)}

        return results

    async def _send_pushplus(self, token: str, title: str, text: str) -> Dict[str, Any]:
        """微信 PushPlus 推送"""
        url = "http://www.pushplus.plus/send"
        payload = {
            "token": token,
            "title": title,
            "content": text,
            "template": "markdown"
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            return {"success": resp.status_code == 200, "text": resp.text}

notify_service = NotifyService()
