resource "aws_db_instance" "this" {
  identifier = var.identifier

  engine         = "postgres"
  engine_version = "17.6"
  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type       = "gp2"

  performance_insights_enabled = true
  performance_insights_retention_period = 7

  db_name  = "app"
  username = "postgres"
  password = var.master_password

  port = 5432

  publicly_accessible     = false
  db_subnet_group_name    = var.db_subnet_group_name
  vpc_security_group_ids  = var.vpc_security_group_ids
  skip_final_snapshot     = true
  deletion_protection     = false
}

output "endpoint" {
  value = aws_db_instance.this.address
}