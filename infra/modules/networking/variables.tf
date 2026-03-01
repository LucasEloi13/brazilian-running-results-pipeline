variable "name_suffix" {
  description = "Sufix for resource names"
  type        = string
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
}
