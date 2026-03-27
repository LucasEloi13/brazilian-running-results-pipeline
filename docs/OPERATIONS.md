# Operations Runbook

Este documento descreve operacao rotineira, sequencia recomendada de execucao e resposta a incidentes.

## Sequencia recomendada (daily batch)

1. Ativar ambiente Python em `spider/`.
2. Rodar `task_extract_and_store_names.py`.
3. Rodar `task_scrape_and_store_results.py`.
4. Rodar `task_export_dimensions.py`.
5. Rodar `infra/scripts/register_new_partitions.py`.
6. Rodar `infra/scripts/csv_to_parquet.py`.
7. Rodar dbt (`dbt run` + `dbt test`).

## Checklist pre-execucao

- Banco PostgreSQL acessivel.
- Credenciais AWS validas para S3, Glue e Athena.
- Bucket S3 configurado em `spider/config/config.yml`.
- Tabelas Glue criadas via Terraform.

## Comandos operacionais

### Spider

```bash
cd spider
source .venv/bin/activate
uv run python task_extract_and_store_names.py
uv run python task_scrape_and_store_results.py
uv run python task_export_dimensions.py
```

### Athena metadata + carga

```bash
python infra/scripts/register_new_partitions.py
python infra/scripts/csv_to_parquet.py
```

### dbt

```bash
cd dbt/running_results
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt run
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt test
```

## Sinais de saude do pipeline

- `extraction_job.status` predominante em `completed`.
- `extraction_task.status` sem crescimento de `failed`.
- Novos objetos CSV em `s3://<bucket>/results/`.
- `dim_results` recebendo novos `job_id` no Athena.
- `dbt test` sem falhas.

## Queries uteis para monitoramento

### Jobs por status

```sql
SELECT status, COUNT(*)
FROM extraction_job
GROUP BY status
ORDER BY status;
```

### Tasks com erro recente

```sql
SELECT id, job_id, modality_id, gender, attempts, error_msg, last_attempt_at
FROM extraction_task
WHERE status = 'failed'
ORDER BY last_attempt_at DESC
LIMIT 50;
```

### Tasks sem upload no S3

```sql
SELECT id, job_id, modality_id, gender
FROM extraction_task
WHERE status = 'completed'
  AND (s3_path IS NULL OR s3_path = '');
```

## Incidentes comuns

### 1) Crescimento de tasks em `failed`

Acoes:

1. Validar `error_msg` em `extraction_task`.
2. Testar algumas `source_url` manualmente.
3. Revisar timeout e delay no `config.yml`.
4. Reprocessar tasks com tentativas pendentes.

### 2) Athena sem novas particoes

Acoes:

1. Executar `register_new_partitions.py --dry-run`.
2. Verificar se CSVs estao no padrao de path esperado:
   `results/state=.../city=.../modality=.../pcd=.../gender=.../event=.../`.
3. Rodar `register_new_partitions.py` sem dry-run.

### 3) dbt sem dados novos

Acoes:

1. Verificar novos `job_id` em `running_results.dim_results`.
2. Reexecutar `csv_to_parquet.py`.
3. Rodar `dbt run --select stg_results+`.

## Manutencao

### Reprocessamento completo de resultados no Athena

```bash
python infra/scripts/csv_to_parquet.py --full-refresh
```

### Reset de schema PostgreSQL (somente ambiente de desenvolvimento)

```bash
cd spider
source .venv/bin/activate
uv run -m src.database.migrations.run_migration --hard-reset
```

## Seguranca

- Nao commitar credenciais em `.env`, `profiles.yml` e `terraform.tfvars`.
- Restringir CIDR de acesso ao RDS.
- Revisar permissoes IAM periodicamente.
