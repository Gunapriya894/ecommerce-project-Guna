output "base_url" {
  value = aws_api_gateway_stage.stage.invoke_url
}

output "guproduct_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/guproduct"
}

output "gucart_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/gucart"
}

output "gurecommend_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/gurecommend"
}

output "gulogu_signup_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/guauth/signup"
}

output "gulogu_login_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/guauth/login"
}

output "gulogu_logout_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/guauth/logout"
}

output "gulogu_verify_url" {
  value = "${aws_api_gateway_stage.stage.invoke_url}/guauth/verify"
}

# ── Frontend Hosting ──────────────────────────────────────────────────────────

output "s3_bucket_name" {
  description = "S3 bucket holding the frontend files"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_url" {
  description = "Your live website URL — open this in browser"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "Use this to invalidate cache after re-uploading files"
  value       = aws_cloudfront_distribution.frontend.id
}
