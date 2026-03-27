# Data Contract (Ingestion -> Lake -> dbt)

Este documento descreve o contrato de dados entre as etapas do pipeline.

## 1) Saida do spider para S3 (results)

Local:

- `s3://<bucket>/results/state=<state>/city=<city>/modality=<distance>/pcd=<bool>/gender=<M|F>/event=<slug>/job_<id>_task_<id>.csv`

Formato:

- CSV UTF-8 com cabecalho.
- Inclui metadados de pipeline e colunas raspadas da pagina.

Campos esperados (ordem relevante para carga Athena incremental):

1. `geral`
2. `cat`
3. `numero`
4. `nome`
5. `equipe`
6. `pace`
7. `tempo`
8. `gap`
9. `raw_row_id`
10. `overall`
11. `category`
12. `bib`
13. `athlete_name`
14. `team`
15. `finish_time`
16. `job_id`
17. `task_id`
18. `event_id`
19. `modality_id`
20. `gender`
21. `distance_km`
22. `is_pcd`
23. `raw_category_name`

## 2) Saida de dimensoes para S3 (dims)

Local:

- `s3://<bucket>/dims/<dimension>/data.parquet`

Dimensoes exportadas:

- `state`
- `city`
- `date`
- `event`
- `modality`
- `extraction_job`
- `extraction_task`

Frequencia:

- `state`: once
- `city` e `date`: weekly
- demais: always

## 3) Contrato Glue/Athena

Database:

- `running_results`

Tabelas de origem para dbt:

- `dim_results`
- `dim_state`
- `dim_city`
- `dim_date`
- `dim_event`
- `dim_modality`
- `dim_extraction_job`
- `dim_extraction_task`

## 4) Contrato dbt

Entrada:

- Sources do schema `running_results` (Glue).

Saida:

- Modelos em schemas de trabalho do dbt (`staging`, `intermediate`, `marts`).
- Modelo final: `fact_results`.

## 5) Regras de compatibilidade

- Alteracoes no schema de `results_csv` exigem alinhamento com:
  - `infra/glue.tf` (definicao de colunas)
  - `infra/scripts/csv_to_parquet.py` (`_TARGET_COLUMNS` e conversoes)
  - modelos dbt de staging/intermediate.
- Alteracoes de colunas em dimensoes exigem alinhamento entre:
  - export em `spider/src/storage/dimensions_storage.py`
  - definicoes em `infra/glue.tf`
  - modelos dbt consumidores.

## 6) Criterios minimos de qualidade

- Nenhum `job_id` novo pode ficar fora de `dim_results` apos carga incremental.
- `dbt test` deve passar antes de publicar camadas analiticas.
- Taxa de falha em `extraction_task` deve permanecer controlada e monitorada.
