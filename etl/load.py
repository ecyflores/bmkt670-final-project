"""Load the schema-shaped CSV files from data/clean into PostgreSQL."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"

# Dimensions must exist before facts; feature rows depend on races and drivers.
TABLE_ORDER = (
    "dim_circuit",
    "dim_driver",
    "dim_race",
    "fact_race_result",
    "fact_driver_standing",
    "fact_weather",
    "ml_features_race_outcome",
)

# These legacy CSV columns have no counterpart in the active Postgres schema.
IGNORED_CSV_COLUMNS = {"team_id"}
BATCH_SIZE = 500


def _read_table_csv(
    table_name: str,
    database_columns: list[str],
    required_columns: set[str],
) -> tuple[list[str], list[tuple[Any, ...]]]:
    csv_path = CLEAN_DIR / f"{table_name}.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Clean CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames
        if not headers:
            raise ValueError(f"{csv_path} is empty or has no header row.")
        if len(headers) != len(set(headers)):
            raise ValueError(f"{csv_path} contains duplicate column names.")

        csv_columns = set(headers)
        database_column_set = set(database_columns)
        unsupported = csv_columns - database_column_set - IGNORED_CSV_COLUMNS
        if unsupported:
            raise ValueError(
                f"{csv_path} contains columns not present in the database table "
                f"{table_name}: {sorted(unsupported)}"
            )
        missing_required_headers = required_columns - csv_columns
        if missing_required_headers:
            raise ValueError(
                f"{csv_path} is missing required database columns: "
                f"{sorted(missing_required_headers)}"
            )

        insert_columns = [column for column in headers if column in database_column_set]
        if not insert_columns:
            raise ValueError(f"{csv_path} has no columns to insert into {table_name}.")

        rows: list[tuple[Any, ...]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(
                    f"{csv_path} row {row_number} has more values than the header."
                )
            values = []
            for column in insert_columns:
                value = row[column]
                value = value.strip() if value is not None else ""
                if not value:
                    if column in required_columns:
                        raise ValueError(
                            f"{csv_path} row {row_number} is missing required "
                            f"value for {column!r}."
                        )
                    values.append(None)
                else:
                    values.append(value)
            rows.append(tuple(values))

    if not rows:
        raise ValueError(f"{csv_path} contains no data rows; refusing to clear the table.")

    ignored = csv_columns & IGNORED_CSV_COLUMNS
    if ignored:
        print(
            f"Ignoring unsupported CSV column(s) for {table_name}: "
            f"{', '.join(sorted(ignored))}"
        )
    return insert_columns, rows


def _table_metadata(cursor, table_name: str) -> tuple[list[str], set[str]]:
    cursor.execute(
        """
        SELECT column_name, is_nullable
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    rows = cursor.fetchall()
    if not rows:
        raise RuntimeError(
            f"Table {table_name!r} was not found in the current schema. "
            "Create the tables first by running `python db_check.py`."
        )
    columns = [row[0] for row in rows]
    required_columns = {name for name, nullable in rows if nullable == "NO"}
    return columns, required_columns


def _insert_rows(cursor, table_name: str, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    for start in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(statement, rows[start : start + BATCH_SIZE])


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    required_settings = ("PGDATABASE", "PGUSER", "PGPASSWORD")
    missing_settings = [
        name for name in required_settings if not os.environ.get(name)
    ]
    if missing_settings:
        raise SystemExit(
            "Missing database settings in environment or .env: "
            f"{', '.join(missing_settings)}"
        )

    connection = psycopg2.connect(
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
    )
    try:
        with connection:
            with connection.cursor() as cursor:
                table_rows: dict[str, tuple[list[str], list[tuple[Any, ...]]]] = {}
                for table_name in TABLE_ORDER:
                    columns, required_columns = _table_metadata(cursor, table_name)
                    table_rows[table_name] = _read_table_csv(
                        table_name,
                        columns,
                        required_columns,
                    )

                # Clear all loaded tables atomically before inserting replacements.
                table_identifiers = sql.SQL(", ").join(
                    sql.Identifier(table_name) for table_name in TABLE_ORDER
                )
                cursor.execute(sql.SQL("TRUNCATE TABLE {} CASCADE").format(table_identifiers))

                for table_name in TABLE_ORDER:
                    insert_columns, rows = table_rows[table_name]
                    _insert_rows(cursor, table_name, insert_columns, rows)
                    print(f"Loaded {len(rows)} rows into {table_name}.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()