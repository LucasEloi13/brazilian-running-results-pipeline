import os
import psycopg
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv(override=True)

class PostgresConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgresConnection, cls).__new__(cls)
            cls._instance._conn = None
        return cls._instance

    def _get_connection(self):
        # Reuse existing connection if open
        if self._conn is None or self._conn.closed:
            timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "15"))
            conn_str = (
                f"host={os.getenv('DB_HOST')} "
                f"port={os.getenv('DB_PORT', 5432)} "
                f"dbname={os.getenv('DB_NAME')} "
                f"user={os.getenv('DB_USER')} "
                f"password={os.getenv('DB_PASSWORD')}"
            )
            try:
                self._conn = psycopg.connect(conn_str, connect_timeout=timeout)
            except Exception as exc:  # psycopg.OperationalError or others
                # fail fast with informative message
                raise RuntimeError(
                    f"Não foi possível conectar ao banco após {timeout}s: {exc}"
                )
        return self._conn

    @contextmanager
    def cursor(self):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()  
        except Exception as e:
            conn.rollback()
            raise e

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None