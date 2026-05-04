import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json"
}

# DynamoDB stores numbers as Decimal — this converts them back to float for JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")

    # Handle CORS preflight
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": HEADERS, "body": "OK"}

    try:
        if http_method == "POST":
            body = event.get("body") or "{}"
            data = json.loads(body)

            item = {
                "user":  str(data.get("user", "")),
                "items": data.get("items", [])
            }
            table.put_item(Item=item)

            return {
                "statusCode": 200,
                "headers": HEADERS,
                "body": json.dumps({"message": "Cart stored", "data": item}, cls=DecimalEncoder)
            }

        else:  # GET
            response = table.scan()
            items = response.get("Items", [])
            return {
                "statusCode": 200,
                "headers": HEADERS,
                "body": json.dumps(items, cls=DecimalEncoder)
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": HEADERS,
            "body": json.dumps({"error": str(e)})
        }
