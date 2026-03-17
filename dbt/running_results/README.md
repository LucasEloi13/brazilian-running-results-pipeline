## Running Results dbt (Athena)

Projeto dbt para arquitetura medalhao sobre Athena/Glue.

### Camadas

- bronze: espelho das tabelas fonte em running_results (dim_*)
- silver: padronizacao de tipos e limpeza minima
- gold: dimensoes analiticas e fato fct_results

### Pre-requisitos

- Perfil AWS eloi-admin configurado localmente
- Bucket running-results-023546157022 existente
- Glue database fonte running_results existente

### Comandos

Rode os comandos a partir da pasta dbt/running_results:

```bash
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt debug
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt parse
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt run
DBT_PROFILES_DIR=.. ../../.venv/bin/dbt test
```

### Destino

Os modelos dbt sao criados no schema Athena running_results_medallion
com dados em s3://running-results-023546157022/medallion/.
