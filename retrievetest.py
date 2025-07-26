import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')  # Change region if needed

knowledge_base_id = "WSGOBUXGKF"
query = "What is Amazon Bedrock?"

response = client.retrieve(
    knowledgeBaseId=knowledge_base_id,
    retrievalQuery={'text': query}
)

# Print retrieved chunks
for chunk in response['retrievalResults']:
    print("Score:", chunk['score'])
    print("Content:", chunk['content']['text'])
    print("Source:", chunk['content'].get('location', {}))
    print("-" * 40)
