from strands.tools.decorator import tool
import boto3
import json
import requests
import time
import os
import datetime
from requests_oauthlib import OAuth1
from botocore.exceptions import ClientError

knowledge_base_id = "WSGOBUXGKF"

SERPER_API_KEY = os.environ.get("SERPER_API_KEY")  

def get_secret():
    secret_name = "xAPICreds"
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret_string = get_secret_value_response['SecretString']
        secrets = json.loads(secret_string)
        return secrets
    except ClientError as e:
        raise RuntimeError(f"Unable to retrieve secret: {e}")

@tool
def myownretrievetool(query: str = None, type: str = "memory", category: str = None, key: str = None) -> str:
    """
    Query both Bedrock Knowledge Base and DynamoDB memories.
    Args:
        query: The search query
        type: Type of content to retrieve (default: "memory")
        category: Category for personal facts
        key: Specific key for the fact (e.g., user phone number)
    Returns:
        str: Retrieved information as a formatted string
    """
    results = []

    try:
        print(f"[RETRIEVE] key={key}, type={type}, category={category}, query='{query}'")

        # Query Bedrock Knowledge Base
        if query:
            client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
            kb_response = client.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={'text': query}
            )
            for chunk in kb_response.get('retrievalResults', []):
                results.append(f"From KB: {chunk['content']['text']}")

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('strands_memory')

        if type == "personal_fact":
            if not key:
                return "Error: 'key' is required when retrieving personal facts."

            if category:
                memory_id = f"fact_{category}_{key}"
                response = table.get_item(Key={'id': memory_id})
                if 'Item' in response:
                    results.append(f"From memory: {response['Item']['content']}")
            else:
                response = table.scan(
                    FilterExpression='begins_with(id, :prefix) AND #k = :key',
                    ExpressionAttributeNames={'#k': 'key'},
                    ExpressionAttributeValues={':prefix': 'fact_', ':key': key}
                )
                if response['Items']:
                    facts = [f"{item.get('category', 'unknown')}: {item['content']}"
                             for item in response['Items']]
                    if facts:
                        results.append("Personal facts:\n" + "\n".join(facts))

        elif type == "memory":
            if not key:
                return "Error: 'key' is required when retrieving memory logs."

            response = table.scan(
                FilterExpression='#type = :type AND #k = :key',
                ExpressionAttributeNames={'#type': 'type', '#k': 'key'},
                ExpressionAttributeValues={':type': type, ':key': key},
                Limit=10
            )
            if response['Items']:
                memories = [f"[{datetime.datetime.fromisoformat(item['date']).strftime('%Y-%m-%d %H:%M:%S')}] {item['content']}"
                            for item in response['Items']]
                results.append("Recent memories:\n" + "\n".join(memories))

        return "\n\n".join(results) if results else "No information found."

    except Exception as e:
        return f"Error retrieving information: {str(e)}"


@tool
def myownstoretool(content: str, type: str = "memory", category: str = None, key: str = None) -> str:
    """
    Store content in DynamoDB.
    Args:
        content: The content to store
        type: Type of content (default: "memory")
        category: Category for personal facts (e.g., "birthday", "favorite_color")
        key: Specific key for the fact (e.g., user phone number)
    Returns:
        str: Confirmation message
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('strands_memory')
        timestamp = int(time.time() * 1000)

        if type == "personal_fact":
            if not category or not key:
                return "Error: 'category' and 'key' are required to store personal facts."
            memory_id = f"fact_{category}_{key}"
        else:
            if not key:
                return "Error: 'key' is required when storing memory logs."
            memory_id = f"{type}_{timestamp}"

        item = {
            'id': memory_id,
            'content': content,
            'type': type,
            'timestamp': timestamp,
            'date': datetime.datetime.now().isoformat(),
            'key': key
        }

        if category:
            item['category'] = category

        table.put_item(Item=item)

        print(f"[STORE] key={key}, type={type}, category={category}, content='{content}'")

        return f"Successfully stored {type}: {category} = {content}" if type == "personal_fact" else f"Successfully stored {type}"

    except Exception as e:
        return f"Error storing content in DynamoDB: {str(e)}"

@tool
def post_tweet(action: str, tweet_text: str = "", tweet_id: str = "") -> str:
    """
    Twitter tool to post, delete, or reply to tweets.
    If deleting and no tweet_id is provided, will try to find the most recent tweet containing the tweet_text.
    """
    API_BASE_URL = "https://api.twitter.com/2"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds between retries

    try:
        secrets = get_secret()
        api_key = secrets['api_key']
        api_secret = secrets['api_secret']
        access_token = secrets['access_token']
        access_token_secret = secrets['access_token_secret']
    except Exception as e:
        return f"Error retrieving secrets: {str(e)}"
        
    def make_request(method, url, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                if method == 'get':
                    response = requests.get(url, **kwargs)
                elif method == 'post':
                    response = requests.post(url, **kwargs)
                elif method == 'delete':
                    response = requests.delete(url, **kwargs)
                
                if response.status_code == 429:  # Too Many Requests
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    return None, "Rate limit exceeded. Please try again later."
                
                response.raise_for_status()
                return response, None
                
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                return None, f"Request failed: {str(e)}"
        
        return None, "Max retries exceeded"

    auth = OAuth1(api_key, api_secret, access_token, access_token_secret)
    headers = {"Content-Type": "application/json"}

    try:
        if action == "post":
            if not tweet_text:
                return "Error: tweet_text is required to post a tweet."
            payload = {"text": tweet_text[:280]}
            response, error = make_request('post', f"{API_BASE_URL}/tweets", auth=auth, headers=headers, json=payload)
            if error:
                return f"Error posting tweet: {error}"

        elif action == "delete":
            if not tweet_id and not tweet_text:
                return "Error: either tweet_id or tweet_text is required to delete a tweet."
            
            # If no tweet_id provided but we have text, try to find the tweet
            if not tweet_id and tweet_text:
                # Get user's recent tweets
                me_response, error = make_request('get', f"{API_BASE_URL}/users/me", auth=auth, headers=headers)
                if error:
                    return f"Error getting user info: {error}"
                user_id = me_response.json()['data']['id']
                
                # Get recent tweets
                tweets_response, error = make_request(
                    'get',
                    f"{API_BASE_URL}/users/{user_id}/tweets",
                    auth=auth,
                    headers=headers,
                    params={"max_results": 10}  # Get last 10 tweets
                )
                if error:
                    return f"Error getting tweets: {error}"
                
                # Find matching tweet
                tweets = tweets_response.json().get('data', [])
                for tweet in tweets:
                    if tweet_text.lower() in tweet['text'].lower():
                        tweet_id = tweet['id']
                        break
                
                if not tweet_id:
                    return f"Could not find recent tweet containing: {tweet_text}"
            
            # Delete the tweet
            response, error = make_request('delete', f"{API_BASE_URL}/tweets/{tweet_id}", auth=auth, headers=headers)
            if error:
                return f"Error deleting tweet: {error}"

        elif action == "reply":
            if not tweet_text or not tweet_id:
                return "Error: tweet_text and tweet_id are required to reply to a tweet."
            payload = {
                "text": tweet_text[:280],
                "reply": {"in_reply_to_tweet_id": tweet_id}
            }
            response, error = make_request('post', f"{API_BASE_URL}/tweets", auth=auth, headers=headers, json=payload)
            if error:
                return f"Error replying to tweet: {error}"

        else:
            return "Error: action must be 'post', 'delete', or 'reply'."

        return response.json()

    except Exception as e:
        return f"Error: {str(e)}"

@tool
def websearch(query: str) -> str:
    """
    Searches Google using Serper.dev and returns the top few results.
    """
    if not SERPER_API_KEY:
        return "Missing API key for web search."

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = { "q": query }

    response = requests.post("https://google.serper.dev/search", headers=headers, json=payload)

    if response.status_code != 200:
        return f"Search failed. Status: {response.status_code}"

    data = response.json()
    results = data.get("organic", [])[:3]

    if not results:
        return "No results found."

    output = []
    for result in results:
        title = result.get("title")
        link = result.get("link")
        snippet = result.get("snippet")
        output.append(f"**{title}**\n{snippet}\n{link}")

    return "\n\n".join(output)