variable "identifier"               { type = string }
variable "master_password"          { type = string }
variable "db_subnet_group_name"     { type = string }
variable "vpc_security_group_ids"   { type = list(string) }