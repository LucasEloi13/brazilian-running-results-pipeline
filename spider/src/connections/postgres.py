"""PostgreSQL database connection manager for RDS."""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class PostgresConnection:
    """
    PostgreSQL connection manager with context manager support.
    
    Provides methods for common database operations like fetch, write, execute, etc.
    Uses connection pooling for better performance.
    
    Example:
        >>> db = PostgresConnection()
        >>> rows = db.fetch_all("SELECT * FROM users WHERE id = %s", (1,))
        >>> db.execute("INSERT INTO users (name) VALUES (%s)", ("John",))
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        autocommit: bool = False,
        connect_timeout: int = 10,
        statement_timeout_ms: Optional[int] = None,
        sslmode: Optional[str] = None,
        sslrootcert: Optional[str] = None,
    ):
        """
        Initialize PostgreSQL connection.

        Args:
            host: Database host (defaults to env var DB_HOST)
            port: Database port (defaults to env var DB_PORT or 5432)
            database: Database name (defaults to env var DB_NAME)
            user: Database user (defaults to env var DB_USER)
            password: Database password (defaults to env var DB_PASSWORD)
            autocommit: Enable autocommit mode
            connect_timeout: Connection timeout in seconds
            statement_timeout_ms: Optional statement timeout in milliseconds
            sslmode: PostgreSQL SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
            sslrootcert: Path to CA certificate bundle file
        """
        self.host = host or os.getenv("DB_HOST")
        self.port = port or int(os.getenv("DB_PORT", 5432))
        self.database = database or os.getenv("DB_NAME")
        self.user = user or os.getenv("DB_USER")
        self.password = password or os.getenv("DB_PASSWORD")
        self.autocommit = autocommit
        self.connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", connect_timeout))
        self.sslmode = sslmode or os.getenv("DB_SSLMODE", "require")
        self.sslrootcert = sslrootcert or os.getenv("DB_SSLROOTCERT")

        env_statement_timeout = os.getenv("DB_STATEMENT_TIMEOUT_MS")
        if statement_timeout_ms is not None:
            self.statement_timeout_ms = statement_timeout_ms
        elif env_statement_timeout:
            self.statement_timeout_ms = int(env_statement_timeout)
        else:
            self.statement_timeout_ms = None

        if not all([self.host, self.database, self.user, self.password]):
            raise ValueError(
                "Missing required database credentials. "
                "Provide via parameters or environment variables: "
                "DB_HOST, DB_NAME, DB_USER, DB_PASSWORD"
            )

        self._connection: Optional[psycopg.Connection] = None

    @property
    def connection_string(self) -> str:
        """Build connection string for PostgreSQL."""
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.user} "
            f"password={self.password}"
        )

    def connect(self) -> psycopg.Connection:
        """
        Establish connection to PostgreSQL.

        Returns:
            Active database connection
        """
        if self._connection is None or self._connection.closed:
            try:
                options = None
                if self.statement_timeout_ms is not None:
                    options = f"-c statement_timeout={self.statement_timeout_ms}"

                self._connection = psycopg.connect(
                    self.connection_string,
                    autocommit=self.autocommit,
                    connect_timeout=self.connect_timeout,
                    options=options,
                    sslmode=self.sslmode,
                    sslrootcert=self.sslrootcert,
                )
                logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
            except psycopg.OperationalError as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise

        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("PostgreSQL connection closed")
            self._connection = None

    @contextmanager
    def get_cursor(self, row_factory=dict_row):
        """
        Context manager for database cursor.

        Args:
            row_factory: Row factory for cursor (default: dict_row)

        Yields:
            Database cursor
        """
        conn = self.connect()
        cursor = conn.cursor(row_factory=row_factory)
        try:
            yield cursor
            if not self.autocommit:
                conn.commit()
        except Exception as e:
            if not self.autocommit:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    def fetch_one(
        self,
        query: str,
        params: Optional[Tuple] = None,
        row_factory=dict_row,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from database.

        Args:
            query: SQL query
            params: Query parameters
            row_factory: Row factory (default: dict_row)

        Returns:
            Single row as dictionary or None
        """
        with self.get_cursor(row_factory=row_factory) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            logger.debug(f"Fetched one row: {query[:100]}...")
            return result

    def fetch_all(
        self,
        query: str,
        params: Optional[Tuple] = None,
        row_factory=dict_row,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all rows from database.

        Args:
            query: SQL query
            params: Query parameters
            row_factory: Row factory (default: dict_row)

        Returns:
            List of rows as dictionaries
        """
        with self.get_cursor(row_factory=row_factory) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            logger.debug(f"Fetched {len(results)} rows: {query[:100]}...")
            return results

    def fetch_many(
        self,
        query: str,
        params: Optional[Tuple] = None,
        size: int = 100,
        row_factory=dict_row,
    ) -> List[Dict[str, Any]]:
        """
        Fetch limited number of rows from database.

        Args:
            query: SQL query
            params: Query parameters
            size: Number of rows to fetch
            row_factory: Row factory (default: dict_row)

        Returns:
            List of rows as dictionaries
        """
        with self.get_cursor(row_factory=row_factory) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchmany(size)
            logger.debug(f"Fetched {len(results)} rows (limit {size}): {query[:100]}...")
            return results

    def execute(
        self,
        query: str,
        params: Optional[Tuple] = None,
    ) -> int:
        """
        Execute a single query (INSERT, UPDATE, DELETE).

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            rowcount = cursor.rowcount
            logger.debug(f"Executed query affecting {rowcount} rows: {query[:100]}...")
            return rowcount

    def execute_many(
        self,
        query: str,
        params_list: List[Tuple],
    ) -> int:
        """
        Execute query with multiple parameter sets (bulk insert/update).

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            rowcount = cursor.rowcount
            logger.debug(f"Executed batch of {len(params_list)} queries affecting {rowcount} rows")
            return rowcount

    def insert(
        self,
        table: str,
        data: Dict[str, Any],
        returning: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Insert a single row into table.

        Args:
            table: Table name
            data: Dictionary with column names and values
            returning: Column to return after insert (e.g., "id")

        Returns:
            Value of returning column or None
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ["%s"] * len(values)

        query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values})").format(
            table=sql.Identifier(table),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(map(sql.SQL, placeholders)),
        )

        if returning:
            query = sql.SQL("{query} RETURNING {column}").format(
                query=query,
                column=sql.Identifier(returning),
            )

        with self.get_cursor() as cursor:
            cursor.execute(query, values)
            if returning:
                result = cursor.fetchone()
                logger.debug(f"Inserted into {table}, returned: {result}")
                return result[returning] if result else None
            logger.debug(f"Inserted into {table}")
            return None

    def bulk_insert(
        self,
        table: str,
        data_list: List[Dict[str, Any]],
    ) -> int:
        """
        Bulk insert multiple rows into table.

        Args:
            table: Table name
            data_list: List of dictionaries with column names and values

        Returns:
            Number of inserted rows
        """
        if not data_list:
            return 0

        columns = list(data_list[0].keys())
        placeholders = ["%s"] * len(columns)

        query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values})").format(
            table=sql.Identifier(table),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(map(sql.SQL, placeholders)),
        )

        params_list = [tuple(row[col] for col in columns) for row in data_list]

        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            rowcount = cursor.rowcount
            logger.info(f"Bulk inserted {rowcount} rows into {table}")
            return rowcount

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: str,
        where_params: Optional[Tuple] = None,
    ) -> int:
        """
        Update rows in table.

        Args:
            table: Table name
            data: Dictionary with column names and new values
            where: WHERE clause (without "WHERE" keyword)
            where_params: Parameters for WHERE clause

        Returns:
            Number of updated rows
        """
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col)) for col in data.keys()
        )

        query = sql.SQL("UPDATE {table} SET {set_clause} WHERE {where}").format(
            table=sql.Identifier(table),
            set_clause=set_clause,
            where=sql.SQL(where),
        )

        params = list(data.values()) + (list(where_params) if where_params else [])

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            rowcount = cursor.rowcount
            logger.debug(f"Updated {rowcount} rows in {table}")
            return rowcount

    def delete(
        self,
        table: str,
        where: str,
        where_params: Optional[Tuple] = None,
    ) -> int:
        """
        Delete rows from table.

        Args:
            table: Table name
            where: WHERE clause (without "WHERE" keyword)
            where_params: Parameters for WHERE clause

        Returns:
            Number of deleted rows
        """
        query = sql.SQL("DELETE FROM {table} WHERE {where}").format(
            table=sql.Identifier(table),
            where=sql.SQL(where),
        )

        with self.get_cursor() as cursor:
            cursor.execute(query, where_params)
            rowcount = cursor.rowcount
            logger.debug(f"Deleted {rowcount} rows from {table}")
            return rowcount

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()
