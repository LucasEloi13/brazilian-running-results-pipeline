variable "aws_region" {
  description = "Aws region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile to use for credentials"
  type        = string
  default     = "default"
}

variable "terraform_role_arn" {
  description = "ARN of the IAM role for Terraform to assume"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "running-results"
}

variable "rds_master_password" {
  description = "Master password for RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}
