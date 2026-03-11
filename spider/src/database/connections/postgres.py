import os
import threading
import psycopg2
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv(override=True)

class PostgresConnection:
    def __init__(self):
        self._local = threading.local()

    def _get_connection(self):
        conn = getattr(self._local, "_conn", None)
        if conn is None or conn.closed:
            timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "15"))
            conn_str = (
                f"host={os.getenv('DB_HOST')} "
                f"port={os.getenv('DB_PORT', 5432)} "
                f"dbname={os.getenv('DB_NAME')} "
                f"user={os.getenv('DB_USER')} "
                f"password={os.getenv('DB_PASSWORD')}"
            )
            try:
                conn = psycopg2.connect(conn_str, connect_timeout=timeout)
                self._local._conn = conn
            except Exception as exc:  # psycopg2.OperationalError or others
                # fail fast with informative message
                raise RuntimeError(
                    f"Não foi possível conectar ao banco após {timeout}s: {exc}"
                )
        return conn

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
        conn = getattr(self._local, "_conn", None)
        if conn:
            conn.close()
            self._local._conn = None