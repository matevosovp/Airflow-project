import os
import argparse
import pandas as pd
from sqlalchemy import create_engine


def build_pg_uri() -> str:
    host = os.getenv("DB_DESTINATION_HOST") 
    port = os.getenv("DB_DESTINATION_PORT") 
    db = os.getenv("DB_DESTINATION_NAME") 
    user = os.getenv("DB_DESTINATION_USER")
    password = os.getenv("DB_DESTINATION_PASSWORD") 

    missing = [k for k, v in {
        "DB_DESTINATION_HOST (или PG_HOST)": host,
        "DB_DESTINATION_NAME (или PG_DB)": db,
        "DB_DESTINATION_USER (или PG_USER)": user,
        "DB_DESTINATION_PASSWORD (или PG_PASSWORD)": password,
    }.items() if not v]

    if missing:
        raise RuntimeError(f"Не заданы переменные окружения для Postgres: {', '.join(missing)}")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="Таблица-источник, например public.real_estate_dataset_clean")
    parser.add_argument("--out", required=True, help="Путь для сохранения CSV")
    args = parser.parse_args()

    uri = build_pg_uri()
    engine = create_engine(uri)

    df = pd.read_sql(f"SELECT * FROM {args.table}", con=engine)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"Saved dataset: {args.out}, rows={len(df)}, cols={df.shape[1]}")


if __name__ == "__main__":
    main()
