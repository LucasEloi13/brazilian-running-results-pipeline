import os
import psycopg
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

class PostgresConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgresConnection, cls).__new__(cls)
            cls._instance._conn = None
        return cls._instance

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            conn_str = (
                f"host={os.getenv('DB_HOST')} "
                f"port={os.getenv('DB_PORT', 5432)} "
                f"dbname={os.getenv('DB_NAME')} "
                f"user={os.getenv('DB_USER')} "
                f"password={os.getenv('DB_PASS')}"
            )
            self._conn = psycopg.connect(conn_str)
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