# variable "name_suffix" {
#   description = "Sufix for resource names"
#   type        = string
# }

# variable "common_tags" {
#   description = "Common tags for all resources"
#   type        = map(string)
# }

# variable "allowed_ip_cidr" {
#   description = "Allowed IP CIDR for RDS access"
#   type        = string
# }


variable "name_suffix" { type = string }
# variable "common_tags" { type = map(string) default = {} }