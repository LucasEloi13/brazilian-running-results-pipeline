# Tags comuns para todos os recursos
locals {
  environment = "personal"

  common_tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
    CreatedAt = timestamp()
  }

  name_suffix = "${var.project_name}-${local.environment}"
}
