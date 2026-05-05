# backend.tf
# Tells Terraform to store its state file in S3
# instead of on your local machine

terraform {
  backend "s3" {
    bucket = "gu-terraform-state-gunapriya"   # your bucket name from Step 5
    key    = "guna-ecommerce/terraform.tfstate"
    region = "ap-southeast-1"
  }
}