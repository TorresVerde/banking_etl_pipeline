
from pathlib import Path
import os
import sys
from getpass import getpass

import pandas as pd
import psycopg


PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "banking_dwh",
    "user": "etl_user",
}

SOURCES = {
    "customers": {
        "file": "customers.csv",
        "columns": [
            "customer_id",
            "full_name",
            "birth_date",
            "registration_date",
            "customer_status",
        ],
    },
    "accounts": {
        "file": "accounts.csv",
        "columns": [
            "account_id",
            "customer_id",
            "account_type",
            "currency",
            "open_date",
            "account_status",
        ],
    },
    "transactions": {
        "file": "transactions.csv",
        "columns": [
            "transaction_id",
            "account_id",
            "transaction_ts",
            "amount",
            "currency",
            "operation_type",
            "transaction_status",
        ],
    },
}


def main():
    # Пароль можно передать из оркестратора через переменную окружения.
    # При самостоятельном запуске загрузчик запросит пароль сам.
    password = os.environ.get("BANKING_ETL_DB_PASSWORD")

    if not password:
        password = getpass("Введите пароль PostgreSQL: ")

    # Сначала проверяем и читаем все CSV.
    # До завершения этой проверки база данных не изменяется.
    prepared_data = {}

    for table_name, config in SOURCES.items():
        file_path = RAW_DIR / config["file"]

        if not file_path.exists():
            raise FileNotFoundError(
                f"Исходный файл не найден: {file_path}"
            )

        df = pd.read_csv(
            file_path,
            sep=";",
            dtype=str,
            keep_default_na=False,
        )

        expected_columns = config["columns"]

        if list(df.columns) != expected_columns:
            raise ValueError(
                f"Неверные столбцы в {file_path.name}. "
                f"Ожидались: {expected_columns}. "
                f"Получены: {list(df.columns)}"
            )

        prepared_data[table_name] = [
            tuple(row)
            for row in df.itertuples(index=False, name=None)
        ]

    # Контекст подключения обеспечивает COMMIT при успехе
    # и ROLLBACK при ошибке.
    with psycopg.connect(
        **DB_CONFIG,
        password=password,
    ) as conn:
        with conn.cursor() as cur:
            for table_name, rows in prepared_data.items():
                cur.execute(f"TRUNCATE TABLE staging.{table_name}")

                if rows:
                    columns_sql = ", ".join(
                        SOURCES[table_name]["columns"]
                    )
                    placeholders = ", ".join(
                        ["%s"] * len(SOURCES[table_name]["columns"])
                    )

                    query = (
                        f"INSERT INTO staging.{table_name} "
                        f"({columns_sql}) VALUES ({placeholders})"
                    )

                    cur.executemany(query, rows)

                print(
                    f"{table_name}: загружено {len(rows)} строк"
                )

    print("Загрузка завершена успешно.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ОШИБКА ЗАГРУЗКИ: {exc}", file=sys.stderr)
        sys.exit(1)
