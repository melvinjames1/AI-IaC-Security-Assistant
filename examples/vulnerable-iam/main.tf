# ============================================================
# DEMO ONLY — Deliberately Vulnerable IAM Configuration
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

# VULNERABILITY 1: Wildcard Action — grants all AWS actions
# CKV_AWS_1: IAM policies should not allow "*" actions
resource "aws_iam_policy" "wildcard_policy" {
  name        = "ai-iac-guard-demo-wildcard"
  description = "AI-IaC Guard Demo — VULNERABLE: wildcard policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "VulnerableWildcardAccess"
        Effect   = "Allow"
        Action   = "*"          # ← CKV_AWS_1: all actions allowed
        Resource = "*"          # ← all resources
      }
    ]
  })
}

# VULNERABILITY 2: Role with wildcard assume-role (trusts all AWS principals)
# CKV_AWS_60: IAM role trust policy should not allow all principals
resource "aws_iam_role" "vulnerable_role" {
  name = "ai-iac-guard-demo-vulnerable-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = "*" }   # ← CKV_AWS_60: trusts any AWS principal
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "AI-IaC Guard Demo — Vulnerable Role"
    Environment = "Demo"
  }
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.vulnerable_role.name
  policy_arn = aws_iam_policy.wildcard_policy.arn
}

# VULNERABILITY 3: IAM user with inline policy (CKV_AWS_40)
resource "aws_iam_user" "service_account" {
  name = "ai-iac-guard-demo-svc"
  tags = {
    Name = "AI-IaC Guard Demo Service Account"
  }
}

# CKV_AWS_40: IAM user should not have an inline policy
resource "aws_iam_user_policy" "inline_policy" {
  name = "inline-admin"
  user = aws_iam_user.service_account.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:*", "ec2:*", "iam:*"]   # ← overly broad
        Resource = "*"
      }
    ]
  })
}

# VULNERABILITY 4: No MFA policy for console users
# CKV_AWS_9: IAM password policy should require MFA (missing MFA enforcement)
resource "aws_iam_account_password_policy" "weak_policy" {
  minimum_password_length        = 6    # ← CKV_AWS_9: too short (should be ≥14)
  require_symbols                = false
  require_numbers                = false
  require_uppercase_characters   = false
  require_lowercase_characters   = false
  allow_users_to_change_password = true
  max_password_age               = 0    # ← Never expires (CKV_AWS_9)
  password_reuse_prevention      = 0    # ← No reuse prevention
}
