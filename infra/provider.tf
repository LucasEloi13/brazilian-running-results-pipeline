provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  assume_role {
    role_arn = var.terraform_role_arn
  }

  default_tags {
    tags = local.common_tags
  }
}
