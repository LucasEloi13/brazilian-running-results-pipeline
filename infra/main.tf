# # Networking (VPC, Security Groups, etc)
# module "networking" {
#   source = "./modules/networking"

#   allowed_ip_cidr = var.allowed_ip_cidr

#   name_suffix = local.name_suffix
#   common_tags = local.common_tags
# }

# module "rds" {
#   source = "./modules/rds"

#   identifier      = local.name_suffix
#   master_password = var.rds_master_password

#   public_subnet_ids      = module.networking.public_subnet_ids
#   db_subnet_group_name   = module.networking.db_subnet_group_name
#   vpc_security_group_ids = [module.networking.rds_security_group_id]

#   common_tags = local.common_tags

#   depends_on = [module.networking]
# }


module "networking" {
  source = "./modules/networking"

  name_suffix = local.name_suffix
  # common_tags = local.common_tags
}

module "bastion_ssm" {
  source = "./modules/bastion_ssm"

  name_suffix = local.name_suffix
  # common_tags = local.common_tags

  subnet_id         = module.networking.private_subnet_ids[0]
  ec2_sg_id         = module.networking.ec2_security_group_id
  instance_profile  = module.networking.ec2_instance_profile_name
}

module "rds" {
  source = "./modules/rds"

  identifier      = local.name_suffix
  master_password = var.rds_master_password
  # common_tags     = local.common_tags

  db_subnet_group_name   = module.networking.db_subnet_group_name
  vpc_security_group_ids = [module.networking.rds_security_group_id]

  depends_on = [module.networking]
}