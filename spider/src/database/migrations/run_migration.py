import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connections.postgres import PostgresConnection

logger = logging.getLogger("RunMigration")


def _split_sql_statements(sql_script: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False

    for char in sql_script:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(char)

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return statements


def run_migration(sql_file: Path | None = None) -> None:
    migration_file = sql_file or Path(__file__).with_name("migration.sql")
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file não encontrado: {migration_file}")

    sql_script = migration_file.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql_script)

    if not statements:
        logger.warning("Nenhum statement SQL encontrado em %s", migration_file)
        return

    db = PostgresConnection()
    logger.info("Iniciando migration: %s", migration_file)

    with db.cursor() as cur:
        for idx, statement in enumerate(statements, start=1):
            cur.execute(statement)
            logger.info("Statement %s/%s executado com sucesso", idx, len(statements))

    logger.info("Migration finalizada com sucesso. %s statements aplicados.", len(statements))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    run_migration()


if __name__ == "__main__":
    main()
