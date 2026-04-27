# Create Lambdas using module

module "guproduct" {
  source        = "./modules/lambda_api"
  function_name = "guproduct"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  source_path   = "guproduct/lambda_function"

  table_name = aws_dynamodb_table.products.name
  table_arn  = aws_dynamodb_table.products.arn
}

module "gucart" {
  source        = "./modules/lambda_api"
  function_name = "gucart"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  source_path   = "gucart/lambda_function"

  table_name = aws_dynamodb_table.cart.name
  table_arn  = aws_dynamodb_table.cart.arn
}

module "gurecommend" {
  source        = "./modules/lambda_api"
  function_name = "gurecommend"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  source_path   = "gurecommend/lambda_function"

  table_name = aws_dynamodb_table.recommend.name
  table_arn  = aws_dynamodb_table.recommend.arn
}

# =========================
# AUTH — DynamoDB Tables
# =========================

resource "aws_dynamodb_table" "users" {
  name         = "gulogu-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "username"

  attribute {
    name = "username"
    type = "S"
  }
}

resource "aws_dynamodb_table" "tokens" {
  name         = "gulogu-tokens"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "token"

  ttl {
    attribute_name = "expiry"
    enabled        = true
  }

  attribute {
    name = "token"
    type = "S"
  }
}

# =========================
# AUTH — IAM Role
# =========================

resource "aws_iam_role" "auth_lambda_role" {
  name = "gulogu-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "auth_basic" {
  role       = aws_iam_role.auth_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "auth_dynamodb_policy" {
  name = "gulogu-dynamodb-policy"
  role = aws_iam_role.auth_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ]
      Resource = [
        aws_dynamodb_table.users.arn,
        aws_dynamodb_table.tokens.arn
      ]
    }]
  })
}

# =========================
# AUTH — Lambda Function
# =========================

data "archive_file" "auth_zip" {
  type        = "zip"
  source_file = "${path.module}/gulogu/lambda_auth.py"
  output_path = "${path.module}/gulogu/lambda_auth.zip"
}

resource "aws_lambda_function" "auth" {
  function_name    = "gulogu"
  filename         = data.archive_file.auth_zip.output_path
  source_code_hash = data.archive_file.auth_zip.output_base64sha256
  role             = aws_iam_role.auth_lambda_role.arn
  handler          = "lambda_auth.lambda_handler"
  runtime          = "python3.11"
  timeout          = 15
  memory_size      = 256

  environment {
    variables = {
      USERS_TABLE  = aws_dynamodb_table.users.name
      TOKENS_TABLE = aws_dynamodb_table.tokens.name
    }
  }
}

# =========================
# SINGLE API GATEWAY
# =========================

resource "aws_api_gateway_rest_api" "main_api" {
  name = "guna-single-api"
}

# ======================
# PRODUCT ROUTE
# ======================

resource "aws_api_gateway_resource" "product" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_rest_api.main_api.root_resource_id
  path_part   = "guproduct"
}

resource "aws_api_gateway_method" "product_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.product.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "product_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.product.id
  http_method             = aws_api_gateway_method.product_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.guproduct.lambda_invoke_arn
}

# ======================
# CART ROUTE
# ======================

resource "aws_api_gateway_resource" "cart" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_rest_api.main_api.root_resource_id
  path_part   = "gucart"
}

resource "aws_api_gateway_method" "cart_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.cart.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "cart_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.cart.id
  http_method             = aws_api_gateway_method.cart_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.gucart.lambda_invoke_arn
}

# ======================
# RECOMMEND ROUTE
# ======================

resource "aws_api_gateway_resource" "recommend" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_rest_api.main_api.root_resource_id
  path_part   = "gurecommend"
}

resource "aws_api_gateway_method" "recommend_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.recommend.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "recommend_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.recommend.id
  http_method             = aws_api_gateway_method.recommend_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.gurecommend.lambda_invoke_arn
}

# ======================
# AUTH ROUTES — /guauth
# ======================

resource "aws_api_gateway_resource" "guauth" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_rest_api.main_api.root_resource_id
  path_part   = "guauth"
}

# /guauth/signup
resource "aws_api_gateway_resource" "auth_signup" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_resource.guauth.id
  path_part   = "signup"
}

resource "aws_api_gateway_method" "auth_signup_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.auth_signup.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "auth_signup_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.auth_signup.id
  http_method             = aws_api_gateway_method.auth_signup_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth.invoke_arn
}

# /guauth/login
resource "aws_api_gateway_resource" "auth_login" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_resource.guauth.id
  path_part   = "login"
}

resource "aws_api_gateway_method" "auth_login_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.auth_login.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "auth_login_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.auth_login.id
  http_method             = aws_api_gateway_method.auth_login_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth.invoke_arn
}

# /guauth/verify
resource "aws_api_gateway_resource" "auth_verify" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_resource.guauth.id
  path_part   = "verify"
}

resource "aws_api_gateway_method" "auth_verify_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.auth_verify.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "auth_verify_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.auth_verify.id
  http_method             = aws_api_gateway_method.auth_verify_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth.invoke_arn
}

# /guauth/logout
resource "aws_api_gateway_resource" "auth_logout" {
  rest_api_id = aws_api_gateway_rest_api.main_api.id
  parent_id   = aws_api_gateway_resource.guauth.id
  path_part   = "logout"
}

resource "aws_api_gateway_method" "auth_logout_method" {
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  resource_id   = aws_api_gateway_resource.auth_logout.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "auth_logout_integration" {
  rest_api_id             = aws_api_gateway_rest_api.main_api.id
  resource_id             = aws_api_gateway_resource.auth_logout.id
  http_method             = aws_api_gateway_method.auth_logout_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth.invoke_arn
}

# ======================
# LAMBDA PERMISSIONS
# ======================

resource "aws_lambda_permission" "product_perm" {
  statement_id  = "AllowAPIGatewayProduct"
  action        = "lambda:InvokeFunction"
  function_name = module.guproduct.function_name
  principal     = "apigateway.amazonaws.com"
}

resource "aws_lambda_permission" "cart_perm" {
  statement_id  = "AllowAPIGatewayCart"
  action        = "lambda:InvokeFunction"
  function_name = module.gucart.function_name
  principal     = "apigateway.amazonaws.com"
}

resource "aws_lambda_permission" "recommend_perm" {
  statement_id  = "AllowAPIGatewayRecommend"
  action        = "lambda:InvokeFunction"
  function_name = module.gurecommend.function_name
  principal     = "apigateway.amazonaws.com"
}

resource "aws_lambda_permission" "auth_perm" {
  statement_id  = "AllowAPIGatewayAuth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main_api.execution_arn}/*/*"
}

# ======================
# DEPLOYMENT
# ======================

resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [
    aws_api_gateway_integration.product_integration,
    aws_api_gateway_integration.cart_integration,
    aws_api_gateway_integration.recommend_integration,
    aws_api_gateway_integration.auth_signup_integration,
    aws_api_gateway_integration.auth_login_integration,
    aws_api_gateway_integration.auth_verify_integration,
    aws_api_gateway_integration.auth_logout_integration,
  ]

  rest_api_id = aws_api_gateway_rest_api.main_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.guauth,
      aws_api_gateway_resource.auth_signup,
      aws_api_gateway_resource.auth_login,
      aws_api_gateway_resource.auth_verify,
      aws_api_gateway_resource.auth_logout,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "stage" {
  stage_name    = "dev"
  rest_api_id   = aws_api_gateway_rest_api.main_api.id
  deployment_id = aws_api_gateway_deployment.deployment.id
}

# =========================
# DYNAMODB TABLES
# =========================

resource "aws_dynamodb_table" "products" {
  name         = "guproduct-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "cart" {
  name         = "gucart-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user"

  attribute {
    name = "user"
    type = "S"
  }
}

resource "aws_dynamodb_table" "recommend" {
  name         = "gurecommend-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}
