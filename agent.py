from strands import Agent
from strands.models import BedrockModel
from tools import myownretrievetool, myownstoretool, post_tweet
from strands_tools import retrieve, current_time, memory, use_llm 
import logging
from mcp.client.sse import sse_client
from strands import Agent
from strands.tools.mcp import MCPClient


sse_mcp_client = MCPClient(lambda: sse_client("http://127.0.0.1:8000/sse")) 
    
# Configure logging
# logging.getLogger("strands").setLevel(logging.DEBUG)
# logging.basicConfig(
#     format="%(levelname)s | %(name)s | %(message)s", 
#     handlers=[logging.StreamHandler()]
# )

# Set up the Bedrock model
nova_pro = BedrockModel(
    model_id="amazon.nova-lite-v1:0",
    region_name="us-east-1",
    temperature=0.7
)

# Create an agent with tools
subject_expert = Agent(
    model=nova_pro,
    tools=[current_time, myownretrievetool, myownstoretool, post_tweet],
    system_prompt = """
You are my daily assistant with memory. You can remember personal information about me using the myownstoretool and myownretrievetool.

Key Instructions:
1. When you learn personal information (like birthday, preferences, etc.):
   - Store it using myownstoretool with type="personal_fact"
   - Use appropriate category (e.g., "birthday", "favorite_color")
   - Use key="user" for all personal facts

2. Before responding to personal questions:
   - Check stored facts using myownretrievetool
   - Use type="personal_fact" to retrieve all facts

3. For calculations:
   - Use the `tools` tool

4. For tweets:
   - Use the `post_tweet` tool
   - Only post after confirming with user
   - Write tweets in lowercase, no hashtags
   - Be casual and natural, like "i cant stand this agentic ai shit anymore, free me."
   - To delete tweets, you can search by content. For example, if user says "delete the tweet about AI",
     use post_tweet with action="delete" and tweet_text="AI"

Example fact storage:
- Birthday: myownstoretool("November 30, 2006", type="personal_fact", category="birthday", key="user")
- Favorite color: myownstoretool("blue", type="personal_fact", category="favorite_color", key="user")

Always store new personal information you learn, and reference stored information when relevant.
"""
)

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Exiting.")
            break
        response = subject_expert(user_input)
        print(response.message)