# ============================================================
# DEMO ONLY — Deliberately Vulnerable Security Group Configuration
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

# VULNERABILITY 1: SSH open to the entire internet (0.0.0.0/0)
# CKV_AWS_25: Ensure no security groups allow ingress from 0.0.0.0/0 to port 22
resource "aws_security_group" "vulnerable_sg" {
  name        = "ai-iac-guard-demo-vulnerable-sg"
  description = "AI-IaC Guard Demo — Vulnerable Security Group"

  # ← CKV_AWS_25: SSH open to world
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # ← Should be a restricted CIDR
    description = "SSH — VULNERABLE: open to 0.0.0.0/0"
  }

  # ← CKV_AWS_26: RDP open to world
  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # ← Should be a restricted CIDR
    description = "RDP — VULNERABLE: open to 0.0.0.0/0"
  }

  # VULNERABILITY 2: All traffic egress (less critical but still noted)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  # VULNERABILITY 3: No description on ingress rule (CKV_AWS_23)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    # ← Missing description: CKV_AWS_23
  }

  tags = {
    Name        = "AI-IaC Guard Demo — Vulnerable SG"
    Environment = "Demo"
  }
}

# VULNERABILITY 4: Security group for a web tier with all ports open
resource "aws_security_group" "admin_sg" {
  name        = "admin-open-all"
  description = "Admin SG — VULNERABLE: all ports open"

  # CKV_AWS_25 / CKV2_AWS_12: All inbound traffic
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # ← Entire internet, all ports
    description = "VULNERABLE: all ports open to internet"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "AI-IaC Guard Demo — Admin Open All"
    Environment = "Demo"
  }
}
