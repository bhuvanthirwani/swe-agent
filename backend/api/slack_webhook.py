from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import time
import os
import json
from typing import Dict, Any

router = APIRouter()

# In a real setup, SLACK_SIGNING_SECRET should be in .env
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "default_secret")

def verify_slack_signature(request: Request, body: bytes) -> bool:
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not slack_signature:
        return False

    # Prevent replay attacks
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, slack_signature)

@router.post("/slack/interactive")
async def slack_interactive(request: Request):
    body = await request.body()
    
    # Optional: Enable signature validation in production
    # if not verify_slack_signature(request, body):
    #    raise HTTPException(status_code=401, detail="Invalid Slack signature")

    # Slack sends interactive payloads as form data with a 'payload' field containing JSON
    form_data = await request.form()
    payload_str = form_data.get("payload")
    if not payload_str:
        raise HTTPException(status_code=400, detail="Missing payload")

    payload = json.loads(payload_str)
    
    # Check for button clicks
    if payload.get("type") == "block_actions":
        actions = payload.get("actions", [])
        for action in actions:
            if action.get("action_id") == "approve_suggestion_action":
                # 1. Map approved suggestion back to a requirements definition
                # 2. Invoke the Universal Agent Runtime or Orchestrator
                print("Suggestion Approved! Triggering Orchestrator...")
                
                # 3. Update the original Slack message in-place
                response_url = payload.get("response_url")
                # httpx.post(response_url, json={"replace_original": "true", "text": "🔄 Implementing feature..."})
                
                return {"text": "Implementation triggered successfully."}
                
            elif action.get("action_id") == "decline_suggestion_action":
                print("Suggestion Declined.")
                return {"text": "Suggestion declined."}

    return {"status": "ok"}
