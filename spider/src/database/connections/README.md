# PostgreSQL RDS Connection

Classe completa de conexão com PostgreSQL RDS criado pelo Terraform.

## 🚀 Quick Start

### 1. Instale as dependências

```bash
cd spider
uv sync  # ou pip install -e .
```

### 2. Configure variáveis de ambiente

```bash
# Copie o exemplo
cp .env.example .env

# Obtenha o endpoint do RDS
cd ../infra
terraform output

# Cole os valores no .env
nano .env
```

### 3. Use a classe

```python
from src.connections import PostgresConnection

# Opção 1: Usa variáveis de ambiente do .env
with PostgresConnection() as db:
    users = db.fetch_all("SELECT * FROM users")
    print(users)

# Opção 2: Passa credenciais manualmente
db = PostgresConnection(
    host="your-rds.us-east-1.rds.amazonaws.com",
    database="runningResult",
    user="postgres",
    password="your-password"
)
```

## 📚 Métodos Disponíveis

### Fetch (Buscar dados)

```python
# Buscar uma linha
user = db.fetch_one("SELECT * FROM users WHERE id = %s", (1,))

# Buscar todas as linhas
users = db.fetch_all("SELECT * FROM users")

# Buscar quantidade limitada
users = db.fetch_many("SELECT * FROM users", size=10)
```

### Write (Escrever dados)

```python
# Insert único
user_id = db.insert(
    table="users",
    data={"name": "John", "email": "john@example.com"},
    returning="id"
)

# Bulk insert (múltiplos)
users = [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
]
count = db.bulk_insert("users", users)

# Update
db.update(
    table="users",
    data={"name": "John Doe"},
    where="id = %s",
    where_params=(1,)
)

# Delete
db.delete(
    table="users",
    where="email = %s",
    where_params=("old@example.com",)
)
```

### Execute (SQL direto)

```python
# Create table
db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100) UNIQUE
    )
""")

# Execute com parâmetros
db.execute(
    "INSERT INTO users (name, email) VALUES (%s, %s)",
    ("John", "john@example.com")
)

# Execute múltiplos (batch)
params_list = [
    ("Alice", "alice@example.com"),
    ("Bob", "bob@example.com"),
]
db.execute_many(
    "INSERT INTO users (name, email) VALUES (%s, %s)",
    params_list
)
```

### Utilidades

```python
# Verificar se tabela existe
exists = db.table_exists("users")

# Context manager (recomendado)
with PostgresConnection() as db:
    # Conexão automática
    db.fetch_all("SELECT 1")
    # Fechamento automático
```

## 🔧 Features

- ✅ **Context Manager**: Gerenciamento automático de conexão
- ✅ **Auto-commit**: Suporte para transações ou autocommit
- ✅ **Dict Rows**: Retorna linhas como dicionários por padrão
- ✅ **Type Hints**: Completamente tipado
- ✅ **Logging**: Logs de operações para debugging
- ✅ **SQL Builder**: Métodos helpers para INSERT, UPDATE, DELETE
- ✅ **Bulk Operations**: Suporte para operações em lote
- ✅ **Error Handling**: Rollback automático em caso de erro

## 📝 Variáveis de Ambiente

```bash
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_NAME=runningResult
DB_USER=postgres
DB_PASSWORD=your-password
```

## 🎯 Exemplo Completo

Ver arquivo: `example_postgres_usage.py`

```bash
python example_postgres_usage.py
```

## 🔐 Segurança

- ❌ Nunca commite o arquivo `.env` com credenciais
- ✅ Use `.env.example` como template
- ✅ Senhas devem ter 16+ caracteres
- ✅ Rotacione senhas periodicamente
- ✅ Use IAM roles em produção quando possível

## 📊 Obtendo Credenciais do Terraform

```bash
cd infra
terraform output

# Outputs:
# rds_endpoint = "running-results-personal-abc123.rds.amazonaws.com:5432"
# rds_database_name = "runningResult"
# rds_username = <sensitive>
```

Para ver senha (se necessário):
```bash
terraform output -json | jq -r '.rds_username.value'
```
