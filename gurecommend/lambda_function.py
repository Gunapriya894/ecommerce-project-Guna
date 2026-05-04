import json
import boto3
import uuid
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

# Keyword-based recommendation map — driven entirely by the product name from the user
RELATED = {
    "laptop":     ["Mouse", "Keyboard", "Laptop Stand", "USB Hub", "Monitor", "Webcam"],
    "mouse":      ["Mouse Pad", "Keyboard", "USB Hub", "Laptop Stand"],
    "keyboard":   ["Mouse", "Wrist Rest", "Keyboard Cover", "USB Hub"],
    "phone":      ["Phone Case", "Screen Protector", "Charger", "Earbuds", "Power Bank"],
    "earbuds":    ["Phone Case", "Charging Cable", "Power Bank"],
    "headphones": ["Amplifier", "Audio Cable", "Carry Case", "Earbuds"],
    "monitor":    ["HDMI Cable", "Monitor Stand", "Webcam", "Keyboard"],
    "tablet":     ["Stylus", "Tablet Case", "Keyboard", "Screen Protector"],
    "charger":    ["Power Bank", "Charging Cable", "USB Hub"],
    "camera":     ["Memory Card", "Camera Bag", "Tripod", "Lens Cleaner"],
    "default":    ["Power Bank", "Charging Cable", "USB Hub", "Carry Bag", "Screen Cleaner"]
}

def get_recommendations(product_name):
    name_lower = product_name.lower()
    for keyword, recs in RELATED.items():
        if keyword == "default":
            continue
        if keyword in name_lower:
            return recs
    return RELATED["default"]

def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")

    # Handle CORS preflight
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": HEADERS, "body": "OK"}

    try:
        if http_method == "POST":
            body = event.get("body") or "{}"
            data = json.loads(body)

            # Product name comes entirely from the frontend/user — nothing hardcoded
            product = str(data.get("product", ""))
            recommendations = get_recommendations(product)

            # Save the lookup for audit purposes
            record = {
                "id":              str(uuid.uuid4()),
                "product":         product,
                "recommendations": recommendations
            }
            table.put_item(Item=record)

            return {
                "statusCode": 200,
                "headers": HEADERS,
                "body": json.dumps({
                    "product":         product,
                    "recommendations": recommendations
                }, cls=DecimalEncoder)
            }

        else:  # GET — return all stored recommendation records
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
