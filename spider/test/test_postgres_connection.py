import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connections.postgres import PostgresConnection


# REQUIRED_DB_ENV_VARS = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASS")


# def _missing_db_env_vars() -> list[str]:
#     return [env_name for env_name in REQUIRED_DB_ENV_VARS if not os.getenv(env_name)]


def test_postgres_connection_is_working() -> None:
    # missing_vars = _missing_db_env_vars()
    # if missing_vars:
    #     pytest.skip(
    #         f"Variáveis de ambiente ausentes para teste de conexão: {', '.join(missing_vars)}"
    #     )

    db = PostgresConnection()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()

        assert result is not None
        assert result[0] == 1
    finally:
        db.close()
