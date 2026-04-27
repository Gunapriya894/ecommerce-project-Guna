# =========================
# IAM ROLE FOR LAMBDA
# =========================
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# =========================
# BASIC EXECUTION POLICY (CloudWatch Logs)
# =========================
resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# =========================
# DYNAMODB ACCESS POLICY (RESTRICTED ✅)
# =========================
resource "aws_iam_role_policy" "dynamodb_policy" {
  name = "${var.function_name}-dynamodb-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Scan"
        ],
        Resource = var.table_arn
      }
    ]
  })
}

# =========================
# LAMBDA FUNCTION
# =========================
resource "aws_lambda_function" "lambda" {
  function_name = var.function_name
  handler       = var.handler
  runtime       = var.runtime

  filename         = "${var.source_path}.zip"
  source_code_hash = filebase64sha256("${var.source_path}.zip")

  role = aws_iam_role.lambda_role.arn

  # =========================
  # ENV VARIABLES
  # =========================
  environment {
    variables = {
      TABLE_NAME = var.table_name
    }
  }
}