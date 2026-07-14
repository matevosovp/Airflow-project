import argparse
import os
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
EXPORT_COLUMNS = (
    "flat_id",
    "building_id",
    "floor",
    "kitchen_area",
    "living_area",
    "rooms",
    "is_apartment",
    "studio",
    "total_area",
    "price",
    "build_year",
    "building_type_int",
    "latitude",
    "longitude",
    "ceiling_height",
    "flats_count",
    "floors_total",
    "has_elevator",
)


def _get_env(primary: str, fallback: str | None = None) -> str | None:
    return os.getenv(primary) or (os.getenv(fallback) if fallback else None)


def build_pg_url() -> URL:
    values = {
        "host": _get_env("DB_DESTINATION_HOST", "PGHOST"),
        "port": _get_env("DB_DESTINATION_PORT", "PGPORT") or "5432",
        "database": _get_env("DB_DESTINATION_NAME", "PGDATABASE"),
        "username": _get_env("DB_DESTINATION_USER", "PGUSER"),
        "password": _get_env("DB_DESTINATION_PASSWORD", "PGPASSWORD"),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing PostgreSQL connection settings: " + ", ".join(missing)
        )

    return URL.create(
        drivername="postgresql+psycopg2",
        username=values["username"],
        password=values["password"],
        host=values["host"],
        port=int(values["port"]),
        database=values["database"],
    )


def quote_table(table: str) -> str:
    parts = table.split(".")
    if len(parts) == 1:
        parts.insert(0, "public")
    if len(parts) != 2 or any(not IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(
            "Table must be an unquoted name in table or schema.table format"
        )
    return ".".join(f'"{part}"' for part in parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream a model-ready PostgreSQL table to CSV"
    )
    parser.add_argument(
        "--table",
        required=True,
        help="Source table, for example public.real_estate_dataset_clean",
    )
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--chunk_size", type=int, default=100_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    table = quote_table(args.table)
    selected_columns = ", ".join(f'"{column}"' for column in EXPORT_COLUMNS)
    query = text(f"SELECT {selected_columns} FROM {table}")

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(f"{output_path}.tmp")

    engine = create_engine(build_pg_url())
    rows_written = 0
    column_count = 0
    first_chunk = True

    try:
        with engine.connect().execution_options(stream_results=True) as connection:
            chunks = pd.read_sql_query(
                query,
                connection,
                chunksize=args.chunk_size,
            )
            for chunk in chunks:
                if chunk.empty:
                    continue
                chunk.to_csv(
                    temporary_path,
                    mode="w" if first_chunk else "a",
                    header=first_chunk,
                    index=False,
                )
                first_chunk = False
                rows_written += len(chunk)
                column_count = len(chunk.columns)

        if first_chunk:
            raise RuntimeError(f"Source table {args.table!r} is empty")

        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        engine.dispose()

    print(
        f"Saved dataset: {output_path}, "
        f"rows={rows_written}, cols={column_count}"
    )


if __name__ == "__main__":
    main()
