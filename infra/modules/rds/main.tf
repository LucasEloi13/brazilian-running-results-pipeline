# resource "aws_db_instance" "postgres" {
#   identifier        = var.identifier
#   engine            = "postgres"
#   engine_version    = var.engine_version
#   instance_class    = var.instance_class
#   allocated_storage = var.allocated_storage
#   storage_type      = "gp2"

#   db_name                = var.db_name
#   username               = var.master_username
#   password               = var.master_password
#   parameter_group_name   = aws_db_parameter_group.postgres.name
#   db_subnet_group_name   = var.db_subnet_group_name
#   vpc_security_group_ids = var.vpc_security_group_ids

#   skip_final_snapshot = true
#   publicly_accessible = true
#   deletion_protection = false

#   enabled_cloudwatch_logs_exports = []
#   monitoring_interval             = 0

#   #tags = var.common_#tags

#   depends_on = [aws_cloudwatch_log_group.rds_logs]
# }

# resource "aws_db_parameter_group" "postgres" {
#   family = "postgres${split(".", var.engine_version)[0]}"
#   name   = "${var.identifier}-postgres-params"

#   parameter {
#     name  = "log_statement"
#     value = "none"
#   }

#   parameter {
#     name  = "log_min_duration_statement"
#     value = "200"
#   }

#   #tags = var.common_#tags
# }

# resource "aws_cloudwatch_log_group" "rds_logs" {
#   name              = "/aws/rds/instance/${var.identifier}/postgresql"
#   retention_in_days = 7

#   #tags = var.common_#tags
# }

resource "aws_db_instance" "this" {
  identifier = var.identifier

  engine         = "postgres"
  engine_version = "16.3"     # ajuste se quiser
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type       = "gp3"

  db_name  = "app"
  username = "postgres"
  password = var.master_password

  port = 5432

  publicly_accessible     = false
  db_subnet_group_name    = var.db_subnet_group_name
  vpc_security_group_ids  = var.vpc_security_group_ids
  skip_final_snapshot     = true
  deletion_protection     = false

  # CloudWatch logs (Postgres)
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  #tags = merge(var.common_#tags, { Name = var.identifier })
}

output "endpoint" {
  value = aws_db_instance.this.address
}