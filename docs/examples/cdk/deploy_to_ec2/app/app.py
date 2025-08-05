from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
from agent_core import process_prompt
import os
import json
import requests

print("WHATSAPP_TOKEN:", os.getenv("WHATSAPP_TOKEN"))
print("PHONE_NUMBER_ID:", os.getenv("PHONE_NUMBER_ID"))

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello from EC2"}

VERIFY_TOKEN = "strands_whatsapp_verify_123"

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Verification failed", status_code=403)

@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    msg = (data.get("entry", [{}])[0]
               .get("changes", [{}])[0]
               .get("value", {})
               .get("messages", [{}])[0])

    prompt = msg.get("text", {}).get("body")
    sender = msg.get("from")

    if not prompt or not sender:
        return PlainTextResponse("Invalid payload", status_code=400)

    response = process_prompt(prompt, sender)
    send_whatsapp_reply(sender, response)

    return PlainTextResponse("OK")

def send_whatsapp_reply(to, message):
    token = "EAARzvOpU08oBPHUBDAFhnSmtJwjlXDFKY3e1BtxxEdZB8j5rgn4u4mSmFu7zUGIuh6wq6ZCBuUHS1d7WSBkzQZCEwMaeUEj1cvCUkXGwtr1ZAHmcck6sICC9x4ZCDDTbckauq5NQX9CoRVdGM3n34DTbmiX2O2VprbehBuSyj84i9Rt8UaORBGRYu510HNsaSnodB8JQRZBa0VnU8e3NRMhBjQzxZACJM6ZBkg2DlosrMLWxgwZDZD"
    phone_number_id = "758008050719293"

    if not token or not phone_number_id:
        print(" Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID")
        return

    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"WhatsApp API request to: {to}")
        print("Payload:", json.dumps(payload, indent=2))
        print("Response:", response.status_code, response.text)

        if not response.ok:
            print("WhatsApp API ERROR")
    except Exception as e:
        print("Exception during WhatsApp reply:", str(e))