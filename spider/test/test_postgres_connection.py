import os
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connections.postgres import PostgresConnection

def test_postgres_connection_is_working() -> None:
    db = PostgresConnection()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()

        assert result is not None
        assert result[0] == 1
    finally:
        db.close()