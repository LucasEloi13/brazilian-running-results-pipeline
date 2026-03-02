# variable "public_subnet_ids" {
#   description = "List of public subnet IDs for RDS subnet group"
#   type        = list(string)
# }

# variable "db_subnet_group_name" {
#   description = "VPC Subnet Group for the RDS"
#   type        = string
# }

# variable "identifier" {
#   description = "The name of the RDS instance"
#   type        = string
#   default     = "runningResult"
# }

# variable "engine_version" {
#   description = "PostgreSQL version (e.g., 16.3)"
#   type        = string
#   default     = "17.6"
# }

# variable "instance_class" {
#   description = "The instance type (Free Tier: db.t3.micro or db.t4g.micro)"
#   type        = string
#   default     = "db.t4g.micro"
# }

# variable "allocated_storage" {
#   description = "Storage in GB (Free Tier limit: 20GB)"
#   type        = number
#   default     = 20
# }

# variable "db_name" {
#   description = "The name of the initial database"
#   type        = string
#   default     = "runningResult"
# }

# variable "master_username" {
#   description = "Master username for the database"
#   type        = string
#   default     = "postgres"
# }

# variable "master_password" {
#   description = "Master password (mark as sensitive)"
#   type        = string
#   sensitive   = true
# }

# # variable "db_subnet_group_name" {
# #   description = "VPC Subnet Group for the RDS"
# #   type        = string
# # }

# variable "vpc_security_group_ids" {
#   description = "Security Groups IDs"
#   type        = list(string)
# }

# variable "common_tags" {
#   description = "Standard tags for resources"
#   type        = map(string)
# }

variable "identifier"               { type = string }
variable "master_password"          { type = string }
variable "db_subnet_group_name"     { type = string }
variable "vpc_security_group_ids"   { type = list(string) }
# variable "common_tags"              { type = map(string) default = {} }