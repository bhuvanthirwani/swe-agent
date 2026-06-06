import os
import httpx
from backend.models.interfaces import SuggestionResult

class SlackConnector:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    async def send_approval_request(self, suggestion: SuggestionResult) -> bool:
        if not self.webhook_url:
            print("Slack webhook URL not configured.")
            return False

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"New Suggestion for {suggestion.project_name}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Title:*\n{suggestion.title}\n\n*Impact Level:*\n{suggestion.impact_level}\n\n*Description:*\n{suggestion.description}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Files Affected:*\n" + "\n".join([f"- `{f}`" for f in suggestion.files_affected])
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve Feature",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": "approve_feature",
                        "action_id": "approve_suggestion_action"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Decline",
                            "emoji": True
                        },
                        "style": "danger",
                        "value": "decline_feature",
                        "action_id": "decline_suggestion_action"
                    }
                ]
            }
        ]

        payload = {"blocks": blocks}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Error sending message to Slack: {e}")
            return False

    async def send_notification(self, title: str, message: str, status: str = "info") -> bool:
        if not self.webhook_url:
            return False
            
        status_emoji = "✅" if status == 'success' else "❌" if status == 'error' else "ℹ️"
        
        payload = {
            "text": f"{status_emoji} *{title}*\n{message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{status_emoji} *{title}*\n{message}"
                    }
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Error sending notification to Slack: {e}")
            return False
