output "rds_endpoint" {
  description = "RDS endpoint for connection"
  value       = module.rds.endpoint
}

output "rds_port" {
  description = "RDS port"
  value       = module.rds.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.database_name
}

output "rds_username" {
  description = "RDS master username"
  value       = module.rds.master_username
  sensitive   = true
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}
