# Infraestrutura (Terraform)

Este diretorio provisiona os recursos AWS do pipeline de corridas.

## Recursos provisionados

- Rede para banco (modulo `networking`).
- Banco PostgreSQL em RDS (modulo `rds`).
- Bucket S3 para resultados e dimensoes.
- Glue Data Catalog:
  - tabelas dimensionais (`dim_state`, `dim_city`, `dim_date`, `dim_event`, `dim_modality`, `dim_extraction_job`, `dim_extraction_task`)
  - tabela bruta de resultados (`results_csv`)
  - tabela curada de resultados (`dim_results`)

## Estrutura

- `main.tf`: wiring dos modulos e recursos centrais.
- `glue.tf`: catalogo Glue/Athena (schema e tabelas externas).
- `provider.tf`: provider AWS e assume-role.
- `variables.tf`: variaveis de entrada.
- `modules/networking`: VPC/sub-redes/security groups.
- `modules/rds`: instancia PostgreSQL.
- `scripts/`: utilitarios de carga e particoes Athena.

## Variaveis obrigatorias

Defina `terraform.tfvars` a partir de `terraform.tfvars.example`:

```hcl
aws_region          = "us-east-1"
aws_profile         = "seu-profile"
terraform_role_arn  = "arn:aws:iam::<account-id>:role/<role-name>"
rds_master_password = "senha-forte"
allowed_ip_cidr     = "X.X.X.X/32"
```

## Ciclo de provisionamento

```bash
cd infra
terraform init
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Outputs importantes

- `rds_endpoint`: endpoint do banco para configurar no `.env` do spider.

## Boas praticas de seguranca

- Restrinja `allowed_ip_cidr` ao menor escopo possivel.
- Nunca commite `terraform.tfvars` com segredos reais.
- Mantenha `rds_master_password` fora de historico e logs.

## Integracao com pipeline de dados

Após o provisionamento:

1. Configure o `.env` do spider com `DB_HOST` apontando para `rds_endpoint`.
2. Ajuste `spider/config/config.yml` para `s3.bucket` e `s3.profile_name`.
3. Execute migracoes e tarefas do spider.
4. Use scripts em `infra/scripts` para manter Athena atualizado.

## Scripts operacionais

### 1) Registro incremental de particoes

```bash
python infra/scripts/register_new_partitions.py
python infra/scripts/register_new_partitions.py --dry-run
```

### 2) Carga incremental CSV -> Parquet (`dim_results`)

```bash
python infra/scripts/csv_to_parquet.py
python infra/scripts/csv_to_parquet.py --full-refresh
```

## Troubleshooting

### `terraform plan` falha por credenciais

- Verifique se o `aws_profile` existe localmente.
- Confirme permissao de `sts:AssumeRole` para `terraform_role_arn`.

### Glue sem dados visiveis no Athena

- Confirme caminhos S3 em `glue.tf`.
- Rode `register_new_partitions.py` para sincronizar metadados de particao.

### Erro de acesso ao bucket

- Verifique policy IAM do profile/role usado pelo spider e pelo Terraform.
- Confira regiao do bucket e profile em `spider/config/config.yml`.
