# Brazilian Running Results Pipeline

Este repositório contém um *spider* Python que extrai dados de corridas do site OpenResults, persiste metadados no PostgreSQL e prepara a base para análises posteriores.

## 📂 Estrutura geral

```
README.md                      # este arquivo
infra/                         # terraform para infraestrutura (RDS, rede etc.)
spider/                         # código Python do extractor e armazenamento
  src/
  test/
  pyproject.toml               # dependências e configuração do uv
  config/config.yml            # parâmetros de scraping
  .venv/                       # virtual env (não versionado)
```

### Principais componentes dentro de `spider/src`

- `database/connections/postgres.py` – singleton de conexão com Postgres
- `database/migrations` – SQL de criação de tabelas + script `run_migration.py`
- `extractors/` – classes que fazem scraping das páginas
- `parses/` – lógica de parsing HTML em objetos dataclass
- `storage/` – persistência com deduplicação baseada em hash do slug
- `main.py` – fluxo principal que faz extração + persistência

## 🛠️ Pré-requisitos

- Python 3.14 ou superior
- PostgreSQL acessível (local ou remoto)
- [`uv`](https://pypi.org/project/uv/) disponível (instalado no `.venv`)
- (Opcional) [Terraform](https://www.terraform.io/) para criar a infra com `infra/`

## 🚀 Configuração do ambiente (venv)

No diretório `spider/` execute:

```bash
python -m venv .venv          # criar ambiente
source .venv/bin/activate     # ativar
pip install --upgrade pip
uv install                    # instala dependências do pyproject.toml
```

Agora o `python`, `uv`, `pytest` etc. referem-se à versão isolada.

> Sempre ative o `.venv` antes de rodar qualquer script/nos comandos abaixo.

## 🔧 Variáveis de ambiente

Crie um `.env` (ou configure no ambiente) com as variáveis de conexão do Postgres:

```env
DB_HOST=localhost
DB_PORT=5432          # opcional
DB_NAME=yourdbname
DB_USER=youruser
DB_PASSWORD=yourpass
DB_CONNECT_TIMEOUT=5   # segundos, opcional
```

O script de migration e os testes dependem dessas variáveis.

## 🗂️ Migrações

Antes de extrair eventos, crie as tabelas no banco com:

```bash
uv run -m src.database.migrations.run_migration
# ou (sem -m) uv run src/database/migrations/run_migration.py
```

O SQL está em `src/database/migrations/migration.sql`; rodar o script várias vezes não causa erro
(devido aos `IF NOT EXISTS`).

## 🕸️ Extração de eventos

Use o `main.py` para buscar corridas e salvar no banco:

```bash
cd spider
source .venv/bin/activate
uv run python main.py
```

O fluxo faz:
1. buscar páginas do endpoint configurado em `config/config.yml`
2. parsear cada evento em dataclasses
3. gravar `state`, `city`, `date`, `event` e `modality` no PostgreSQL
   - gera o `hash_slug` determinístico (MD5 do slug)
   - ignora corridas cujo hash já exista para evitar duplicatas

Logs são escritos em `logs/app.log`.

## ✅ Testes

Um teste `test_postgres_connection.py` garante que a conexão com PostgreSQL
funciona; ele será pulado se as variáveis de ambiente não estiverem definidas.

Para rodar todos os testes:

```bash
uv run pytest -q
```

Adicione novos casos na pasta `test/` seguindo o mesmo padrão.

## 🧠 Como reproduzir problemas

1. Ative o `.venv`
2. Garanta que as variáveis do banco estão corretas
3. Execute a migration (`uv run -m src.database.migrations.run_migration`)
4. Execute `uv run python main.py` e observe os logs ou saídas no console
5. Se o script falhar, inspecione as mensagens na tela/log e verifique a
   conexão/estruturas de tabela no banco.

## 💡 Dicas adicionais

- A classe `PostgresConnection` inclui um timeout configurável e fecha a
  conexão automaticamente.
- O `EventNameStorage` é responsável por deduplicar e armazenar os eventos.
- As tabelas suportam reingestão incremental sem sobrescrever dados úteis.

---

Este projeto serve como base para um pipeline de ingestão concreto. Sinta-se
à vontade para estender com novos extractors, armazenamento em S3, análise
posterior, etc. Boa corrida! 🏃‍♂️
