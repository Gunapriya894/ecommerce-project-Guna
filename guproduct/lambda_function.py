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

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")

    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": HEADERS, "body": "OK"}

    try:
        if http_method == "POST":
            body = event.get("body") or "{}"
            data = json.loads(body)

            # ID comes from the user — no auto-generation
            product_id = str(data.get("id", "")).strip()
            if not product_id:
                return {
                    "statusCode": 400,
                    "headers": HEADERS,
                    "body": json.dumps({"error": "Product ID is required"})
                }

            item = {
                "id":    product_id,
                "name":  str(data.get("name", "")),
                "price": Decimal(str(data.get("price", 0))),
                "stock": int(data.get("stock", 0))
            }
            table.put_item(Item=item)

            return {
                "statusCode": 200,
                "headers": HEADERS,
                "body": json.dumps({"message": "Product stored", "data": item}, cls=DecimalEncoder)
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