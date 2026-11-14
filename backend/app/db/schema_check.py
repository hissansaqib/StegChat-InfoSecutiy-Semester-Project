"""Startup database schema verification."""

from sqlalchemy import inspect
from ..core.logging import logger
from ..db.base import Base

class SchemaDriftError(RuntimeError):
    """Raised when the database schema does not match the SQLAlchemy model definitions."""
    pass

def check_schema_sync(engine) -> None:
    """Compare SQLAlchemy Base.metadata models against the actual SQLite database.
    
    Fails loudly and clearly if any required table or column is missing.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables = []
    missing_columns = []

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            missing_tables.append(table_name)
            continue

        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        for model_col in table.columns:
            if model_col.name not in existing_cols:
                missing_columns.append(f"{table_name}.{model_col.name}")

    if missing_tables or missing_columns:
        error_lines = [
            "\n" + "=" * 70,
            "CRITICAL DATABASE SCHEMA MISMATCH DETECTED ON STARTUP!",
            "=" * 70,
        ]
        if missing_tables:
            error_lines.append(f"Missing tables: {', '.join(missing_tables)}")
        if missing_columns:
            error_lines.append(f"Missing columns: {', '.join(missing_columns)}")
        error_lines.extend([
            "",
            "To fix this schema drift, run either:",
            "  alembic upgrade head",
            "or reset the dev database with:",
            "  powershell scripts/reset_db.ps1",
            "=" * 70 + "\n",
        ])
        err_msg = "\n".join(error_lines)
        logger.error(err_msg)
        raise SchemaDriftError(err_msg)

    logger.info("Database schema verification passed: all models match DB structure.")

