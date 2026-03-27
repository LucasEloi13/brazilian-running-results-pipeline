# Running Results dbt (Athena)

Projeto dbt para modelagem analitica sobre dados do pipeline de corridas,
usando Athena + Glue Data Catalog.

## Objetivo

Transformar tabelas brutas e dimensionais do schema `running_results` em modelos
curados para analise.

## Arquitetura de camadas

1. `staging`:
	- padronizacao inicial e renomeacao de colunas.
	- fontes definidas em `models/staging/stg_sources.yml`.
2. `intermediate`:
	- regras de normalizacao e preparacao para joins analiticos.
3. `marts`:
	- modelo final `fact_results` para consumo BI/analytics.

## Fontes esperadas

Catalogadas no Glue database `running_results`:

- `dim_results`
- `dim_state`
- `dim_city`
- `dim_date`
- `dim_event`
- `dim_modality`
- `dim_extraction_job`
- `dim_extraction_task`

## Pre-requisitos

- dbt Core instalado com adapter Athena.
- AWS profile com permissao de leitura/escrita no bucket e Athena.
- Arquivo de profile dbt configurado.

## Configuracao de profile

### Modelo base

Use `profiles.example.yml` como referencia.

### Exemplo (`dbt/profiles.yml`)

```yaml
running_results:
  target: dev
  outputs:
	 dev:
		type: athena
		threads: 4
		aws_profile_name: eloi-admin
		region_name: us-east-1
		database: awsdatacatalog
		schema: dbt
		s3_staging_dir: s3://running-results-<account-id>/dbt-staging/
		s3_data_dir: s3://running-results-<account-id>/dbt-models/
		s3_data_naming: table_unique
		work_group: primary
```

## Comandos principais

Executar a partir de `dbt/running_results`:

```bash
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt debug
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt parse
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt run
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt test
```

Operacao seletiva:

```bash
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt run --select staging
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt run --select intermediate
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt run --select marts.fact_results
```

## Modelo final

`models/marts/fact_results.sql` entrega um dataset analitico unificando:

- dados de resultados (`int_results`)
- atributos de eventos (`int_events`)
- atributos de modalidades (`int_modalities`)

Principais colunas de saida:

- identificadores: `event_id`, `modality_id`
- dimensoes: estado, cidade, data, modalidade, categoria
- metricas e atributos: colocacao geral, pace, tempo final, gap

## Qualidade e validacao

Recomendado em pipeline CI/CD:

1. `dbt parse`
2. `dbt run`
3. `dbt test`

## Troubleshooting

### `dbt debug` falha por profile

- Confirme `DBT_PROFILES_DIR=..`.
- Verifique nome do profile no `dbt_project.yml` (`profile: running_results`).

### Tabelas source nao encontradas

- Verifique se Glue tables existem no database `running_results`.
- Garanta que o pipeline de ingestao executou export e carga previamente.

### Sem dados no marts

- Confirme populacao de `dim_results` no Athena.
- Reexecute carga incremental:
  - `python infra/scripts/register_new_partitions.py`
  - `python infra/scripts/csv_to_parquet.py`
