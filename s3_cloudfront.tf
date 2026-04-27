##############################################################################
# GU Commerce — S3 + CloudFront Static Hosting
# Add this file as:  s3_cloudfront.tf  in your project root
# Then run: terraform init -upgrade && terraform apply
##############################################################################

# ── S3 Bucket ─────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket        = "gu-commerce-frontend-${random_id.suffix.hex}"
  force_destroy = true
}

resource "random_id" "suffix" {
  byte_length = 4
}

# Block ALL public access — CloudFront will access via OAC, not public URLs
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning (good practice)
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ── CloudFront Origin Access Control ─────────────────────────────────────────

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "gu-commerce-oac"
  description                       = "OAC for GU Commerce frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ── S3 Bucket Policy — allow only CloudFront OAC ─────────────────────────────

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAC"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_cloudfront_distribution.frontend]
}

# ── CloudFront Distribution ───────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "login.html"
  price_class         = "PriceClass_100" # US, Europe, Asia — cheapest

  comment = "GU Commerce Frontend"

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    # Short cache for HTML files so updates reflect quickly
    min_ttl     = 0
    default_ttl = 300   # 5 minutes
    max_ttl     = 1200  # 20 minutes
  }

  # SPA-style: redirect 403/404 back to login.html
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/login.html"
    error_caching_min_ttl = 10
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/login.html"
    error_caching_min_ttl = 10
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Project = "gu-commerce"
  }
}

# ── Upload HTML files to S3 ───────────────────────────────────────────────────

locals {
  frontend_files = {
    "login.html"          = "frontend/login.html"
    "index.html"          = "frontend/index.html"
    "product.html"        = "frontend/product.html"
    "cart.html"           = "frontend/cart.html"
    "recommendation.html" = "frontend/recommendation.html"
  }
}

resource "aws_s3_object" "frontend_files" {
  for_each = local.frontend_files

  bucket       = aws_s3_bucket.frontend.id
  key          = each.key
  source       = each.value
  content_type = "text/html"
  etag         = filemd5(each.value)
}
