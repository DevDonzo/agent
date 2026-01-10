# Autonomous Real Estate Agent

This project is a multi-faceted AI assistant that can be interacted with via the command line or WhatsApp. It uses a `strands` agent with Amazon Bedrock for its core logic, and has tools for memory, knowledge retrieval, and posting to Twitter.

## Features

- **Command-line Interface**: Interact with the agent directly from your terminal.
- **WhatsApp Integration**: Chat with the agent through WhatsApp.
- **Memory**: The agent can remember personal information using a DynamoDB table.
- **Knowledge Retrieval**: The agent can retrieve information from a Bedrock Knowledge Base.
- **Twitter Integration**: The agent can post, delete, and reply to tweets on your behalf.

## Project Structure

- `agent.py`: The main entry point for the AI agent.
- `tools.py`: Implements the custom tools for the agent.
- `whatsapp_handler.py`: A Flask application that acts as a webhook for the WhatsApp Business API.
- `calculator_mcp_server.py`: A microservice that exposes a calculator function.
- `requirements.txt`: The Python dependencies for the project.
- `templates/`: Contains the HTML template for the privacy policy.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/DevDonzo/autonomous-real-estate-agent.git
    cd autonomous-real-estate-agent
    ```

2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up the environment variables:**

    Create a `.env` file in the root of the project and add the following environment variables. You can use the `.env.example` file as a template.

    ```bash
    # For WhatsApp integration
    WHATSAPP_TOKEN=
    VERIFY_TOKEN=
    PHONE_NUMBER_ID=

    # For AWS
    AWS_ACCESS_KEY_ID=
    AWS_SECRET_ACCESS_KEY=
    AWS_REGION=us-east-1

    # For Twitter
    # You need to store your Twitter API credentials in AWS Secrets Manager
    # with the secret name 'xAPICreds'.
    # The secret should be a JSON object with the following keys:
    # "api_key", "api_secret", "access_token", "access_token_secret"

    # For Bedrock Knowledge Base
    KNOWLEDGE_BASE_ID=
    ```

4.  **Create the DynamoDB table:**

    The agent uses a DynamoDB table named `strands_memory` to store memories and personal facts. You can use the `create_dynamodb_table.py` script to create the table.

    ```bash
    python create_dynamodb_table.py
    ```

5.  **Run the application:**

    You can run the agent from the command line:

    ```bash
    python agent.py
    ```

    To run the WhatsApp integration, you'll need to use a tool like `ngrok` to expose the Flask application to the internet.

    ```bash
    ngrok http 8080
    ```

    Then, run the Flask application:

    ```bash
    python whatsapp_handler.py
    ```

    You can also run the calculator service:

    ```bash
    python calculator_mcp_server.py
    ```

## Usage

Once the application is running, you can interact with the agent through the command line or WhatsApp. The agent will respond to your messages and can use the available tools to perform tasks like storing information, retrieving facts, or posting tweets.
