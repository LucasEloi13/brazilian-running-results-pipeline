module "networking" {
  source = "./modules/networking"

  name_suffix = local.name_suffix
}

module "bastion_ssm" {
  source = "./modules/bastion_ssm"

  name_suffix = local.name_suffix

  subnet_id         = module.networking.private_subnet_ids[0]
  ec2_sg_id         = module.networking.ec2_security_group_id
  instance_profile  = module.networking.ec2_instance_profile_name
}

module "rds" {
  source = "./modules/rds"

  identifier      = local.name_suffix
  master_password = var.rds_master_password

  db_subnet_group_name   = module.networking.db_subnet_group_name
  vpc_security_group_ids = [module.networking.rds_security_group_id]

  depends_on = [module.networking]
}