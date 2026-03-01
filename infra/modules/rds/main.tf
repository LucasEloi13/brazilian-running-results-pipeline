resource "aws_db_instance" "postgres" {
  identifier        = var.identifier
  engine            = "postgres"
  engine_version    = var.engine_version
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  storage_type      = "gp2"

  db_name                = var.db_name
  username               = var.master_username
  password               = var.master_password
  parameter_group_name   = aws_db_parameter_group.postgres.name
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.vpc_security_group_ids

  skip_final_snapshot = true
  publicly_accessible = false
  deletion_protection = false

  enabled_cloudwatch_logs_exports = []
  monitoring_interval             = 0

  tags = var.common_tags

  depends_on = [aws_cloudwatch_log_group.rds_logs]
}

resource "aws_db_parameter_group" "postgres" {
  family = "postgres${split(".", var.engine_version)[0]}"
  name   = "${var.identifier}-postgres-params"

  parameter {
    name  = "log_statement"
    value = "none"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "200"
  }
}

resource "aws_cloudwatch_log_group" "rds_logs" {
  name              = "/aws/rds/instance/${var.identifier}/postgresql"
  retention_in_days = 7

  tags = var.common_tags
}