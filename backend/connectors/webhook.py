import httpx
from datetime import datetime

class WebhookConnector:
    def __init__(self, url: str = None):
        self.url = url

    async def send_notification(self, title: str, message: str, status: str = "info", metadata: dict = None) -> bool:
        if not self.url:
            print("Webhook URL not configured.")
            return False

        payload = {
            "event": "pipeline_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "title": title,
            "message": message,
            "status": status,
            "metadata": metadata or {}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Error sending generic webhook: {e}")
            return False
