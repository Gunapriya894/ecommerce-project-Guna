import json
import boto3
import os
import hashlib
import hmac
import secrets
import time
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
users_table  = dynamodb.Table(os.environ['USERS_TABLE'])
tokens_table = dynamodb.Table(os.environ['TOKENS_TABLE'])

HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json"
}

TOKEN_TTL_SECONDS = 86400  # 24 hours


# ── Helpers ────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """SHA-256 + random salt — no external libs needed in Lambda."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split(":")
    if len(parts) != 2:
        return False
    salt, hashed = parts
    return hmac.compare_digest(
        hashlib.sha256((salt + password).encode()).hexdigest(),
        hashed
    )


def generate_token() -> str:
    return secrets.token_hex(32)


def store_token(username: str, token: str):
    expiry = int(time.time()) + TOKEN_TTL_SECONDS
    tokens_table.put_item(Item={
        "token":    token,
        "username": username,
        "expiry":   expiry
    })


def verify_token(token: str):
    """Returns username if valid, None otherwise."""
    try:
        resp = tokens_table.get_item(Key={"token": token})
        item = resp.get("Item")
        if not item:
            return None
        if int(time.time()) > int(item.get("expiry", 0)):
            tokens_table.delete_item(Key={"token": token})
            return None
        return item["username"]
    except Exception:
        return None


def ok(body: dict) -> dict:
    return {"statusCode": 200, "headers": HEADERS, "body": json.dumps(body)}


def err(code: int, msg: str) -> dict:
    return {"statusCode": code, "headers": HEADERS, "body": json.dumps({"error": msg})}


# ── Route handlers ─────────────────────────────────────────────────────────────

def handle_signup(data: dict) -> dict:
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    email    = str(data.get("email", "")).strip().lower()

    if not username or not password or not email:
        return err(400, "username, password, and email are required")
    if len(username) < 3:
        return err(400, "Username must be at least 3 characters")
    if len(password) < 6:
        return err(400, "Password must be at least 6 characters")
    if "@" not in email:
        return err(400, "Invalid email address")

    # Check duplicate
    existing = users_table.get_item(Key={"username": username}).get("Item")
    if existing:
        return err(409, "Username already exists")

    users_table.put_item(Item={
        "username":    username,
        "password":    hash_password(password),
        "email":       email,
        "created_at":  int(time.time())
    })

    token = generate_token()
    store_token(username, token)

    return ok({
        "message":  "Account created successfully",
        "token":    token,
        "username": username,
        "email":    email
    })


def handle_login(data: dict) -> dict:
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return err(400, "username and password are required")

    user = users_table.get_item(Key={"username": username}).get("Item")
    if not user:
        return err(401, "Invalid username or password")

    if not verify_password(password, user["password"]):
        return err(401, "Invalid username or password")

    token = generate_token()
    store_token(username, token)

    return ok({
        "message":  "Login successful",
        "token":    token,
        "username": username,
        "email":    user.get("email", "")
    })


def handle_verify(headers: dict) -> dict:
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    token = auth.replace("Bearer ", "").strip()
    if not token:
        return err(401, "No token provided")

    username = verify_token(token)
    if not username:
        return err(401, "Token is invalid or expired")

    return ok({"valid": True, "username": username})


def handle_logout(headers: dict) -> dict:
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    token = auth.replace("Bearer ", "").strip()
    if token:
        try:
            tokens_table.delete_item(Key={"token": token})
        except Exception:
            pass
    return ok({"message": "Logged out"})


# ── Entry point ────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    method = event.get("httpMethod", "POST")
    path   = event.get("path", "")

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": HEADERS, "body": "OK"}

    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        body = {}

    headers = event.get("headers") or {}

    if "/signup" in path:
        return handle_signup(body)
    elif "/login" in path:
        return handle_login(body)
    elif "/verify" in path:
        return handle_verify(headers)
    elif "/logout" in path:
        return handle_logout(headers)
    else:
        return err(404, "Route not found")
## this was my existing lambda code for auth service 