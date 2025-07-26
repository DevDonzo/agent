from flask import Flask, request, render_template
import requests
from agent import subject_expert
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')

def send_whatsapp_message(phone_number, message):
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Use v17.0 since that's what was working before
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    
    # Ensure message is a string
    if isinstance(message, dict):
        message = str(message)
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }
    
    print(f"Sending message to WhatsApp API:")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        response_json = response.json()
        print(f"Response JSON: {response_json}")
        return response_json
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Error response: {e.response.text}")
        raise

@app.route('/')
def home():
    return "AI Assistant WhatsApp Service"

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    # Handle WhatsApp webhook verification
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"\n=== Webhook Verification ===")
    print(f"Mode: {mode}")
    print(f"Received token: {token}")
    print(f"Challenge: {challenge}")
    print(f"Expected token: {VERIFY_TOKEN}")
    
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("Verification successful!")
            return challenge
        else:
            print("Verification failed!")
    return 'Invalid verification token'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    try:
        if (data and 'entry' in data and data['entry'] 
            and 'changes' in data['entry'][0] 
            and 'value' in data['entry'][0]['changes'][0] 
            and 'messages' in data['entry'][0]['changes'][0]['value']):
            
            message = data['entry'][0]['changes'][0]['value']['messages'][0]
            phone_number = message['from']
            message_text = message.get('text', {}).get('body', '')
            
            if message_text:
                agent_response = subject_expert(message_text)
                message_text = (agent_response.message['content'][0]['text']
                              .replace("<thinking>", "")
                              .replace("</thinking>", "")
                              .strip())
                send_whatsapp_message(phone_number, message_text)
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
    
    return 'OK'

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
