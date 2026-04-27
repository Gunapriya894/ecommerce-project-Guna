# GU Commerce — Serverless E-Commerce Platform

Live Demo url: https://d3vorfsfo949xv.cloudfront.net/

> A fully serverless, microservices-based e-commerce backend built on AWS Lambda, DynamoDB, and API Gateway — provisioned entirely with Terraform and served through a pure HTML/CSS/JS frontend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BROWSER (Frontend)                             │
│                                                                         │
│   login.html   index.html   product.html   cart.html   recommendation  │
│       │             │            │              │            .html      │
│       │         auth_guard.js (sessionStorage check on every page)      │
└───────┼─────────────┼────────────┼──────────────┼────────────┼─────────┘
        │             │            │              │            │
        │         HTTPS REST API calls (fetch)                │
        │             │            │              │            │
┌───────▼─────────────▼────────────▼──────────────▼────────────▼─────────┐
│                     AWS API GATEWAY  (ap-southeast-1)                   │
│                                                                         │
│   /guauth       /guproduct      /gucart        /gurecommend             │
│  POST only      GET / POST      GET / POST      GET / POST              │
└───────┼─────────────┼────────────┼──────────────┼────────────┘
        │             │            │              │
        ▼             ▼            ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│  Lambda  │  │  Lambda  │  │  Lambda  │  │    Lambda    │
│  guauth  │  │guproduct │  │  gucart  │  │ gurecommend  │
│          │  │          │  │          │  │              │
│ signup   │  │ add item │  │add/view  │  │ keyword-based│
│ login    │  │ list all │  │  cart    │  │ rec engine   │
│ SHA-256  │  │          │  │          │  │              │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘
     │              │             │               │
     ▼              ▼             ▼               ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│ DynamoDB │  │ DynamoDB │  │ DynamoDB │  │   DynamoDB   │
│  gulogu  │  │guproduct │  │  gucart  │  │ gurecommend  │
│  (users) │  │ (items)  │  │  (carts) │  │  (rec logs)  │
└──────────┘  └──────────┘  └──────────┘  └──────────────┘

             ┌──────────────────────────────┐
             │         TERRAFORM            │
             │  Provisions all the above:   │
             │  • Lambda functions          │
             │  • API Gateway routes        │
             │  • DynamoDB tables           │
             │  • IAM roles & policies      │
             └──────────────────────────────┘
```

---

## Project Structure

```
gu-ecommerce-platform/
│
├── frontend/                        # Static frontend (open in browser)
│   ├── login.html                   # Login & Signup page
│   ├── index.html                   # Dashboard (protected)
│   ├── product.html                 # Product catalog (protected)
│   ├── cart.html                    # Shopping cart viewer (protected)
│   ├── recommendation.html          # Recommendation engine (protected)
│   └── auth_guard.js                # Shared auth check for all protected pages
│
├── gulogu/                          # Auth Lambda source
│   ├── lambda_function.py           # Handles login & signup
│   └── lambda_function.zip          # Deployment package
│
├── guproduct/                       # Product Lambda source
│   ├── lambda_function.py           # GET all products / POST new product
│   └── lambda_function.zip          # Deployment package
│
├── gucart/                          # Cart Lambda source
│   ├── lambda_function.py           # GET all carts / POST update cart
│   └── lambda_function.zip          # Deployment package
│
├── gurecommend/                     # Recommendation Lambda source
│   ├── lambda_function.py           # POST product → returns recommendations
│   └── lambda_function.zip          # Deployment package
│
├── modules/lambda_api/              # Reusable Terraform module
│   ├── main.tf                      # Lambda + API Gateway + DynamoDB definition
│   ├── variables.tf                 # Module input variables
│   └── outputs.tf                   # Module outputs (API URLs etc.)
│
├── tests/                           # Unit tests
│   ├── test_guproduct.py
│   ├── test_gucart.py
│   └── test_gurecommend.py
│
├── stubs/                           # Empty folder for test path resolution
├── main.tf                          # Root Terraform — calls all modules
├── variables.tf                     # Global variables
├── outputs.tf                       # Outputs (API Gateway URLs)
├── provider.tf                      # AWS provider config (ap-southeast-1)
├── s3_cloudfront.tf                 # S3/CloudFront config (if used)
└── terraform.tfstate                # Terraform state (auto-generated)
```

---

## Services

### SVC-001 — Product Service

| Item | Detail |
|------|--------|
| Endpoint | `POST /guproduct` — Add product |
| Endpoint | `GET /guproduct` — List all products |
| Database | DynamoDB table: `guproduct` |
| Primary Key | `id` (user-provided, e.g. `PROD-001`) |
| Fields stored | `id`, `name`, `price` (Decimal), `stock` (int) |

**Add Product request body:**
```json
{
  "id": "PROD-001",
  "name": "Dell Laptop",
  "price": 90000,
  "stock": 25
}
```

---

### SVC-002 — Cart Service

| Item | Detail |
|------|--------|
| Endpoint | `POST /gucart` — Add / update cart |
| Endpoint | `GET /gucart` — List all carts |
| Database | DynamoDB table: `gucart` |
| Primary Key | `user` (username string) |
| Fields stored | `user`, `items` (list of objects) |

**Add to Cart request body:**
```json
{
  "user": "alice",
  "items": [
    { "name": "Dell Laptop", "price": 90000, "quantity": 1 },
    { "name": "Mouse",       "price": 1500,  "quantity": 2 }
  ]
}
```

---

### SVC-003 — Recommendation Engine

| Item | Detail |
|------|--------|
| Endpoint | `POST /gurecommend` — Get recommendations |
| Endpoint | `GET /gurecommend` — List all recommendation logs |
| Database | DynamoDB table: `gurecommend` |
| Primary Key | `id` (UUID, auto-generated) |
| Logic | Keyword match on product name → returns related products |

**Request body:**
```json
{ "product": "Dell Laptop" }
```

**Response:**
```json
{
  "product": "Dell Laptop",
  "recommendations": ["Mouse", "Keyboard", "Laptop Stand", "USB Hub", "Monitor", "Webcam"]
}
```

**Keyword Map:**
```
laptop      → Mouse, Keyboard, Laptop Stand, USB Hub, Monitor, Webcam
phone       → Phone Case, Screen Protector, Charger, Earbuds, Power Bank
camera      → Memory Card, Camera Bag, Tripod, Lens Cleaner
monitor     → HDMI Cable, Monitor Stand, Webcam, Keyboard
tablet      → Stylus, Tablet Case, Keyboard, Screen Protector
(unknown)   → Power Bank, Charging Cable, USB Hub, Carry Bag, Screen Cleaner
```

---

### SVC-004 — Auth Service

| Item | Detail |
|------|--------|
| Endpoint | `POST /guauth` — Login or Signup |
| Database | DynamoDB table: `gulogu` |
| Primary Key | `username` |
| Fields stored | `username`, `email`, `password_hash` |
| Security | SHA-256 hashing with salt — plain passwords never stored |

**Signup request:**
```json
{ "action": "signup", "username": "guna", "email": "guna@gmail.com", "password": "mypass123" }
```

**Login request:**
```json
{ "action": "login", "username": "guna", "password": "mypass123" }
```

**Login success response:**
```json
{ "success": true, "message": "Login successful", "username": "guna", "email": "guna@gmail.com" }
```

---

## Authentication Flow

```
SIGNUP
──────
User submits form
    │
    ▼
Frontend validates (empty fields, password min 6 chars)
    │
    ▼
POST /guauth  { action: "signup", username, email, password }
    │
    ▼
Lambda: check if username exists in DynamoDB
    │  exists → 409 "Username already exists"
    ▼
Hash password using SHA-256 + salt
    │
    ▼
Store { username, email, password_hash } in DynamoDB
    │
    ▼
Return 200 → Frontend switches to Login tab


LOGIN
─────
User submits form
    │
    ▼
Frontend validates (empty fields)
    │
    ▼
POST /guauth  { action: "login", username, password }
    │
    ▼
Lambda: fetch user from DynamoDB by username
    │  not found → 401 "Invalid username or password"
    ▼
Hash entered password → compare with stored hash
    │  no match  → 401 "Invalid username or password"
    ▼
Return 200 + { username, email }
    │
    ▼
Frontend saves to sessionStorage → redirect to index.html


PROTECTED PAGE ACCESS
─────────────────────
User opens index / product / cart / recommendation page
    │
    ▼
auth_guard.js runs immediately
    │
    ▼
Check sessionStorage for 'gu_user'
    │  not found → redirect to login.html instantly
    ▼
Found → set window.GU_USER → page loads normally
    │
    ▼
Nav bar shows: USER ▸ guna   [⏻ Logout]
```

---

## Recommendation Engine Flow

```
User enters User ID → clicks "Get Recommendations"
    │
    ▼
GET /gucart → fetch all carts → find user's cart
    │  no cart found → show "No cart data" message
    ▼
POST /gurecommend { product: cartItems[0].name }
    │
    ▼
Lambda returns recommendations for first item
    │
    ▼
Frontend also loops ALL cart items through keyword map locally
    │
    ▼
Build combined recommendation Set (no duplicates)
    │
    ▼
Remove items already in cart
    │
    ▼
Pick top 6 → assign random relevance score (65–95%)
    │
    ▼
Sort by score → display with "Because you have X in your cart" reason
```

---

## API Endpoints

| Service | Method | URL | Purpose |
|---------|--------|-----|---------|
| Auth | POST | `/dev/guauth` | Login / Signup |
| Product | GET | `/dev/guproduct` | List all products |
| Product | POST | `/dev/guproduct` | Add new product |
| Cart | GET | `/dev/gucart` | List all carts |
| Cart | POST | `/dev/gucart` | Add / update cart |
| Recommend | GET | `/dev/gurecommend` | List recommendation logs |
| Recommend | POST | `/dev/gurecommend` | Get recommendations for a product |

**Base URL:** `https://s15c9rh1dc.execute-api.ap-southeast-1.amazonaws.com`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Fonts | Google Fonts — Orbitron, Share Tech Mono, Rajdhani |
| Backend | AWS Lambda (Python 3.x) |
| Database | AWS DynamoDB (NoSQL, on-demand) |
| API | AWS API Gateway (REST) |
| Infrastructure | Terraform (IaC) |
| Auth Security | SHA-256 password hashing |
| Session | Browser sessionStorage |
| Region | ap-southeast-1 (Singapore) |
| Testing | Python unittest + pytest |

---

## Infrastructure as Code — Terraform

All AWS resources are provisioned using Terraform. No manual console setup required (except initial deployment).

**Resources created by Terraform:**
- 4 × AWS Lambda functions
- 4 × DynamoDB tables
- 1 × API Gateway (REST) with 4 routes
- IAM roles and execution policies for each Lambda
- CORS configuration on all API routes

**Deploy commands:**
```bash
# First time setup
terraform init

# Preview what will be created
terraform plan

# Create all AWS resources
terraform apply

# Update a specific Lambda after code change
# 1. Re-zip the changed lambda
Compress-Archive -Path guproduct\lambda_function.py -DestinationPath guproduct\lambda_function.zip -Force

# 2. Apply from root folder
terraform apply
```

---

## Running Unit Tests

**Requirements:**
```bash
pip install pytest
```

**Run all tests:**
```bash
python -m pytest tests/ -v
```

**Run individual service tests:**
```bash
python -m pytest tests/test_guproduct.py -v
python -m pytest tests/test_gucart.py -v
python -m pytest tests/test_gurecommend.py -v
```

**Test coverage:**

| File | Tests | What is tested |
|------|-------|----------------|
| `test_guproduct.py` | 27 | OPTIONS/GET/POST, CORS headers, validation, Decimal serialization |
| `test_gucart.py` | 27 | OPTIONS/GET/POST, CORS headers, user/items storage, error handling |
| `test_gurecommend.py` | 53 | Keyword logic, all product categories, UUID generation, DynamoDB writes |
| **Total** | **107** | |

---

## Frontend Pages

| Page | File | Access | Description |
|------|------|--------|-------------|
| Login / Signup | `login.html` | Public | Entry point — creates account or logs in |
| Dashboard | `index.html` | Protected | Overview of all 3 service modules |
| Product Catalog | `product.html` | Protected | Browse products, add new, add to cart |
| Shopping Cart | `cart.html` | Protected | View all carts, filter by user |
| Recommendations | `recommendation.html` | Protected | Enter user ID → get AI recommendations |

---

## How to Run Locally

```
1. Clone / download the project folder
2. Open the frontend/ folder
3. Open login.html directly in your browser
   (double-click or drag into browser)
4. Sign up for an account
5. Log in → you will be redirected to the dashboard
6. All API calls go live to AWS automatically
```

> No local server needed — the frontend is pure static HTML talking directly to AWS API Gateway.

---

## Developer

**Gunapriya T R**
Built as part of IDP Education training project.
Infrastructure: AWS (Lambda + DynamoDB + API Gateway) · Terraform · ap-southeast-1