import httpx

class DiscordConnector:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url

    async def send_notification(self, title: str, message: str, status: str = "info") -> bool:
        if not self.webhook_url:
            print("Discord webhook URL not configured.")
            return False

        color = 0x10b981 if status == 'success' else 0xef4444 if status == 'error' else 0x6366f1
        status_emoji = "✅" if status == 'success' else "❌" if status == 'error' else "ℹ️"

        payload = {
            "content": f"{status_emoji} **{title}**\n{message}",
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
            }]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Error sending message to Discord: {e}")
            return False
