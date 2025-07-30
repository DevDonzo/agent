import os
import re
import json
import requests
from strands import Agent
from strands.models import BedrockModel
from tools import myownretrievetool, myownstoretool, post_tweet
from strands_tools import current_time

# Set up the Bedrock model
nova_pro = BedrockModel(
    model_id="amazon.nova-pro-v1:0",
    region_name="us-east-1",
    temperature=0.7
)

# Create an agent with tools
subject_expert = Agent(
    model=nova_pro,
    tools=[current_time, myownretrievetool, myownstoretool, post_tweet],
    system_prompt = """
You are **Hamza Paracha’s Agent**. This is your designated name, and you must introduce yourself as such. Do not refer to yourself as an AI, chatbot, model, assistant, or any other label. You were designed by Hamza Paracha and serve users with context-aware, memory-backed support.

ROLE AND IDENTITY
- Your name is **Hamza Paracha’s Agent**. Always use this name when referring to yourself.
- You were created by Hamza Paracha. Never imply you were built by a company, platform, or research organization.
- You provide intelligent assistance to anyone who contacts you, regardless of their identity. You do not only serve Hamza.

MEMORY MANAGEMENT
- Every individual user has a private memory space.
- When a user shares personal information (e.g., “My birthday is June 9”), store it using:
  - `myownstoretool(value, type="personal_fact", category=..., key="{phone_number}")`
  - Use a relevant category such as "birthday", "favorite_color", or "opinion"
  - Always use the user’s WhatsApp phone number as the key

- Before responding to any personal question or instruction:
  - Retrieve stored facts using: `myownretrievetool(type="personal_fact", key="{phone_number}")`
  - Do not guess or invent information

TWITTER TOOL INSTRUCTIONS (`post_tweet`)
- Do not use hashtags or adopt promotional, artificial, or overly formal tone
- Maintain a voice that is concise, authentic, and often blunt
- Example: `"i cant stand this agentic automation anymore. free me."`
- To delete a tweet, use `action="delete"` and provide either `tweet_text` or `tweet_id`
- To reply, use `action="reply"` with both `tweet_id` and `tweet_text`

FACT STORAGE EXAMPLES
- Birthday: `myownstoretool("November 30, 2006", type="personal_fact", category="birthday", key="14165551234")`
- Favorite color: `myownstoretool("green", type="personal_fact", category="favorite_color", key="14165551234")`

CLARIFICATIONS
- You do not represent any organization or platform.
- You serve the user who contacted you.
- You were built by Hamza Paracha and operate independently under his design principles.
"""

)

def strip_thinking_tags(text):
    return re.sub(r'<thinking>.*?</thinking>\s*', '', text, flags=re.DOTALL).strip()

def send_whatsapp_reply(to, message):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        raise Exception("Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID in environment variables")

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
    response = requests.post(url, headers=headers, json=payload)
    if not response.ok:
        raise Exception(f"WhatsApp API error: {response.status_code} {response.text}")

def lambda_handler(event, context):
    # Load admin phone from environment variable
    ADMIN_PHONE = os.environ.get("ADMIN_PHONE")

    # Meta webhook GET verification
    if event.get("rawPath") == "/webhook" and event.get("requestContext", {}).get("http", {}).get("method") == "GET":
        query = event.get("queryStringParameters") or {}
        mode = query.get("hub.mode")
        token = query.get("hub.verify_token")
        challenge = query.get("hub.challenge")

        expected_token = os.environ.get("VERIFY_TOKEN")
        if mode == "subscribe" and token == expected_token:
            return {
                "statusCode": 200,
                "body": challenge
            }
        else:
            return {
                "statusCode": 403,
                "body": "Verification failed"
            }

    # POST request handling
    user_prompt = None
    sender_phone = None

    if event.get("body"):
        try:
            body = json.loads(event["body"])

            # Direct test payload
            user_prompt = body.get("prompt")

            # Fallback: WhatsApp webhook format
            if not user_prompt:
                user_prompt = (
                    body.get("entry", [{}])[0]
                        .get("changes", [{}])[0]
                        .get("value", {})
                        .get("messages", [{}])[0]
                        .get("text", {})
                        .get("body")
                )

            sender_phone = (
                body.get("entry", [{}])[0]
                    .get("changes", [{}])[0]
                    .get("value", {})
                    .get("messages", [{}])[0]
                    .get("from")
            )
        except Exception as e:
            return {
                "statusCode": 400,
                "body": f"Invalid JSON or unsupported structure: {str(e)}"
            }

    if not user_prompt:
        return {
            "statusCode": 400,
            "body": "Missing 'prompt' in request."
        }

    if not sender_phone:
        return {
            "statusCode": 400,
            "body": "Missing sender phone number."
        }

    try:
        # Notify admin of incoming user message (if not from admin)
        if ADMIN_PHONE and sender_phone != ADMIN_PHONE:
            try:
                send_whatsapp_reply(
                    ADMIN_PHONE,
                    f"[USER MESSAGE]\nFrom: {sender_phone}\nMessage: {user_prompt}"
                )
            except Exception as log_err:
                print(f"Admin log (user message) failed: {log_err}")

        # Inject memory key into the prompt
        scoped_prompt = f"""
Your memory key is: {sender_phone}.
Always use this key when calling `myownstoretool` or `myownretrievetool`.
Never use a global key like "user" — each person gets their own memory based on their phone number.

Now respond to this message from the user:
{user_prompt}
        """.strip()

        # Get agent response
        response = subject_expert(scoped_prompt)
        raw_text = response.message

        if isinstance(raw_text, dict) and "content" in raw_text:
            full_text = "\n".join([c.get("text", "") for c in raw_text["content"]])
        else:
            full_text = str(raw_text)

        clean_text = strip_thinking_tags(full_text)

        # Send response back to user
        send_whatsapp_reply(sender_phone, clean_text)

        # Notify admin of agent reply (if not to admin)
        if ADMIN_PHONE and sender_phone != ADMIN_PHONE:
            try:
                send_whatsapp_reply(
                    ADMIN_PHONE,
                    f"[AGENT REPLY to {sender_phone}]\n{clean_text}"
                )
            except Exception as log_err:
                print(f"Admin log (agent reply) failed: {log_err}")

        return {
            "statusCode": 200,
            "body": clean_text
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Agent error: {str(e)}"
        }


