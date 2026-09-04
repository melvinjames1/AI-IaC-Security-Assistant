# ============================================================
# DEMO ONLY — Deliberately Vulnerable S3 Bucket Configuration
# DO NOT deploy this to any real environment.
# This file exists solely for Checkov static analysis demonstration.
# ============================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  # Demo credentials — never real, never used for deployment
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  access_key = "demo_access_key"
  secret_key = "demo_secret_key"
}

# VULNERABILITY 1: Public ACL enabled — bucket is publicly readable
resource "aws_s3_bucket" "vulnerable_bucket" {
  bucket = "ai-iac-guard-demo-vulnerable"

  tags = {
    Name        = "AI-IaC Guard Demo — Vulnerable"
    Environment = "Demo"
  }
}

# VULNERABILITY 2: Public access block NOT configured — allows public access
resource "aws_s3_bucket_acl" "vulnerable_acl" {
  bucket = aws_s3_bucket.vulnerable_bucket.id
  acl    = "public-read"   # ← CKV_AWS_20: public-read ACL
}

# VULNERABILITY 3: No server-side encryption configured
# Missing: aws_s3_bucket_server_side_encryption_configuration
# CKV_AWS_19: Ensure all data stored in the S3 bucket is securely encrypted at rest

# VULNERABILITY 4: No versioning enabled
# Missing: aws_s3_bucket_versioning
# CKV_AWS_21: Ensure all data stored in the S3 bucket has versioning enabled

# VULNERABILITY 5: No access logging enabled
# Missing: aws_s3_bucket_logging
# CKV_AWS_18: Ensure the S3 bucket has access logging enabled

# VULNERABILITY 6: No MFA delete protection
# CKV2_AWS_61: Ensure MFA delete is enabled on S3 bucket

# VULNERABILITY 7: Public access block not fully configured
resource "aws_s3_bucket_public_access_block" "vulnerable" {
  bucket = aws_s3_bucket.vulnerable_bucket.id

  block_public_acls       = false   # ← should be true
  block_public_policy     = false   # ← should be true
  ignore_public_acls      = false   # ← should be true
  restrict_public_buckets = false   # ← should be true
}
