module "networking" {
  source = "./modules/networking"

  name_suffix     = local.name_suffix
  allowed_ip_cidr = var.allowed_ip_cidr
}

module "rds" {
  source = "./modules/rds"

  identifier          = local.name_suffix
  master_password     = var.rds_master_password
  publicly_accessible = true

  db_subnet_group_name   = module.networking.db_subnet_group_name
  vpc_security_group_ids = [module.networking.rds_security_group_id]

  depends_on = [module.networking]
}

# S3 Bucket for running results
resource "aws_s3_bucket" "running_results" {
  bucket = "running-results-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    local.common_tags,
    {
      Name = "running-results"
    }
  )
}

# Enable versioning on S3 bucket
resource "aws_s3_bucket_versioning" "running_results" {
  bucket = aws_s3_bucket.running_results.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption on S3 bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "running_results" {
  bucket = aws_s3_bucket.running_results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Data source to get current AWS account ID
data "aws_caller_identity" "current" {}

output "rds_endpoint" {
  description = "RDS endpoint address"
  value       = module.rds.endpoint
}