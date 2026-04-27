provider "aws" {
  region  = "ap-southeast-1"
  profile = "idp-sbx-trn-lab-01"
}

# Required for CloudFront (always us-east-1)
provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = "idp-sbx-trn-lab-01"
}