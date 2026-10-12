import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def main():
    load_dotenv()

    required = ("PGDATABASE", "PGUSER", "PGPASSWORD", "PGHOST", "PGPORT")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit(
            f"Missing database settings in environment or .env: {', '.join(missing)}"
        )

    schema_sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
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
                cursor.execute(schema_sql)
                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = current_schema()
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
                tables = cursor.fetchall()
    finally:
        connection.close()

    print("Tables in the current schema:")
    for (table_name,) in tables:
        print(f"- {table_name}")
    if not tables:
        print("(none found)")


if __name__ == "__main__":
    main()