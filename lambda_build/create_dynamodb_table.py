import boto3

def create_memory_table():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create the table
    table = dynamodb.create_table(
        TableName='strands_memory',
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    
    # Wait until the table exists
    table.meta.client.get_waiter('table_exists').wait(TableName='strands_memory')
    print("Table created successfully!")

if __name__ == "__main__":
    create_memory_table()
