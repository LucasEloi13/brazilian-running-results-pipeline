variable "name_suffix"        { type = string }
# variable "common_tags"        { type = map(string) default = {} }
variable "subnet_id"          { type = string }
variable "ec2_sg_id"          { type = string }
variable "instance_profile"   { type = string }