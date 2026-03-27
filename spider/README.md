# Spider: Extracao de Corridas

Componente responsavel por extrair dados do OpenResults, persistir metadados no PostgreSQL,
gravar resultados brutos em S3 e exportar dimensoes para consumo analitico.

## Componentes principais

- `main.py`: simulacao de orquestracao local (task 1 + task 2).
- `task_extract_and_store_names.py`: coleta eventos e persiste dimensoes basicas.
- `task_scrape_and_store_results.py`: descobre modalidades, processa fila de tarefas e envia CSV ao S3.
- `task_export_dimensions.py`: exporta tabelas dimensionais para Parquet no S3.
- `src/database/migrations`: schema SQL e executor de migracoes.
- `src/extractors`: extratores HTTP/HTML por etapa.
- `src/storage`: persistencia no PostgreSQL + upload S3.

## Setup rapido

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install uv
uv sync
```

## Configuracao

### Variaveis de ambiente (`.env`)

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=running_results
DB_USER=postgres
DB_PASSWORD=postgres
DB_CONNECT_TIMEOUT=15
```

### Configuracao de pipeline (`config/config.yml`)

Campos relevantes:

- `pipeline.extraction_mode`: `paged` ou `full`.
- `pipeline.pages`: paginas quando em modo paginado.
- `pipeline.batch_size`: lote de insercao de eventos.
- `result_pipeline.batch_size`: quantidade de jobs por lote.
- `result_pipeline.task_workers`: paralelismo de tasks de resultados.
- `result_pipeline.max_attempts_total`: maximo de tentativas por task.
- `s3.bucket`, `s3.region`, `s3.results_prefix`, `s3.profile_name`.

## Banco de dados

### Rodar migracao

```bash
uv run -m src.database.migrations.run_migration
```

### Reset completo (destrutivo)

```bash
uv run -m src.database.migrations.run_migration --hard-reset
```

## Execucao

### Pipeline completo local

```bash
uv run python main.py
```

### Pipeline por tarefa

```bash
uv run python task_extract_and_store_names.py
uv run python task_scrape_and_store_results.py
uv run python task_export_dimensions.py
```

## Comportamento das etapas

### Task 1: eventos

1. Itera eventos vindos da API.
2. Persiste `state`, `city`, `date` e `event`.
3. Cria/atualiza `extraction_job` para controle da etapa 2.

### Task 2: resultados

1. Busca jobs pendentes/falhos em `extraction_job`.
2. Descobre modalidades/genero por evento.
3. Cria/atualiza `modality` e `extraction_task`.
4. Executa scraping por task em paralelo.
5. Salva CSV em S3 (`results/...`).
6. Atualiza status de task/job e metadados de processamento.

### Export de dimensoes

Exporta tabelas para `dims/<dimension>/data.parquet` com politica de frequencia:

- `once`: exporta uma unica vez.
- `weekly`: exporta no intervalo semanal.
- `always`: exporta em toda execucao.

## Testes

```bash
uv run pytest -q
```

## Logs

- Arquivo padrao: `logs/app.log`.
- Nivel e destino configurados em `config/config.yml`.

## Troubleshooting

### Erro de conexao com banco

- Confirme `.env` e acesso de rede ao host PostgreSQL.
- Teste conectividade com cliente SQL externo.

### Task de resultados falhando repetidamente

- Verifique `error_msg` em `extraction_task`.
- Confirme validade de `source_url` extraida.
- Aumente `max_attempts_total` apenas se necessario.

### Upload S3 nao ocorre

- Valide `s3.bucket`/`s3.profile_name` em `config/config.yml`.
- Confirme permissao de escrita no bucket.
