output "endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "port" {
  description = "Porta RDS"
  value       = aws_db_instance.postgres.port
}

output "database_name" {
  description = "Nome do banco de dados"
  value       = aws_db_instance.postgres.db_name
}

output "master_username" {
  description = "Username master"
  value       = aws_db_instance.postgres.username
  sensitive   = true
}

output "resource_id" {
  description = "Resource ID da instância RDS"
  value       = aws_db_instance.postgres.resource_id
}
