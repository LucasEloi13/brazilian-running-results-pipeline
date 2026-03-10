import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connections.postgres import PostgresConnection

logger = logging.getLogger("RunMigration")


def _print_usage() -> None:
    """Print usage instructions."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    Database Migration Script                       ║
╚════════════════════════════════════════════════════════════════════╝

USAGE:
    python run_migration.py              # Executes normal migration
    python run_migration.py --hard-reset # Reset + Migration (with confirmation)

DESCRIPTION:
    • Normal: Creates tables if they don't exist (idempotent)
    • --hard-reset: Destroys ALL tables and recreates from scratch (irreversible!)

⚠️  WARNING: The --reset flag discards ALL data!
    
EXAMPLE:
    $ python run_migration.py --hard-reset
    Type 'yes' to confirm the reset: yes
    [Tables destroyed and recreated]
""")


def _split_sql_statements(sql_script: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    dollar_quote_tag: str | None = None
    index = 0

    while index < len(sql_script):
        char = sql_script[index]
        next_char = sql_script[index + 1] if index + 1 < len(sql_script) else ""

        if in_line_comment:
            buffer.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            buffer.append(char)
            if char == "*" and next_char == "/":
                buffer.append(next_char)
                in_block_comment = False
                index += 2
                continue
            index += 1
            continue

        if dollar_quote_tag:
            if sql_script.startswith(dollar_quote_tag, index):
                buffer.append(dollar_quote_tag)
                index += len(dollar_quote_tag)
                dollar_quote_tag = None
                continue

            buffer.append(char)
            index += 1
            continue

        if not in_single_quote and not in_double_quote:
            if char == "-" and next_char == "-":
                buffer.append(char)
                buffer.append(next_char)
                in_line_comment = True
                index += 2
                continue

            if char == "/" and next_char == "*":
                buffer.append(char)
                buffer.append(next_char)
                in_block_comment = True
                index += 2
                continue

            if char == "$":
                closing_index = sql_script.find("$", index + 1)
                if closing_index != -1:
                    candidate_tag = sql_script[index : closing_index + 1]
                    tag_body = candidate_tag[1:-1]
                    if tag_body.replace("_", "").isalnum() or candidate_tag == "$$":
                        buffer.append(candidate_tag)
                        dollar_quote_tag = candidate_tag
                        index = closing_index + 1
                        continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            buffer.append(char)
            index += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            buffer.append(char)
            index += 1
            continue

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            index += 1
            continue

        buffer.append(char)
        index += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return statements


def run_migration(sql_file: Path | None = None) -> None:
    migration_file = sql_file or Path(__file__).with_name("migration.sql")
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    sql_script = migration_file.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql_script)

    if not statements:
        logger.warning("No SQL statements found in %s", migration_file)
        return

    db = PostgresConnection()
    logger.info("Starting migration: %s", migration_file)

    with db.cursor() as cur:
        for idx, statement in enumerate(statements, start=1):
            cur.execute(statement)
            logger.info("Statement %s/%s executed successfully", idx, len(statements))

    logger.info("Migration completed successfully. %s statements applied.", len(statements))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    
    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        _print_usage()
        return
    
    # Check for --hard-reset flag
    should_reset = "--hard-reset" in sys.argv
    
    if should_reset:
        logger.warning("=" * 80)
        logger.warning("⚠️  WARNING: Running RESET — all tables will be destroyed!")
        logger.warning("=" * 80)
        
        # Request confirmation
        response = input("\nType 'yes' to confirm the complete reset: ")
        if response.lower() != "yes":
            logger.info("Reset cancelled by user.")
            return
        
        reset_file = Path(__file__).with_name("reset_migration.sql")
        run_migration(sql_file=reset_file)
        logger.info("Reset completed. Running standard migration...")
    
    # Execute normal migration
    run_migration()


if __name__ == "__main__":
    main()
