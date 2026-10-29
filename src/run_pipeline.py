
from pathlib import Path
import os
import subprocess
import sys
from getpass import getpass

import psycopg


PROJECT_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_DIR / "sql"
SRC_DIR = PROJECT_DIR / "src"

LOADER_SCRIPT = SRC_DIR / "load_to_staging.py"
QUALITY_SCRIPT = SRC_DIR / "check_pipeline_quality.py"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "banking_dwh",
    "user": "etl_user",
}

SQL_FILES = [
    "03_transformations.sql",
    "04_analytics.sql",
]


def main():
    print("=== BANKING ETL PIPELINE ===")

    # Запрашиваем пароль один раз для всех этапов.
    password = getpass("Введите пароль PostgreSQL: ")

    env = os.environ.copy()
    env["BANKING_ETL_DB_PASSWORD"] = password

    # Этап 1. Загрузка исходных данных.
    print("\n[1/4] Загрузка исходных данных...")

    subprocess.run(
        [sys.executable, str(LOADER_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    # Этап 2. SQL-трансформации и аналитика.
    print("\n[2/4] Выполнение SQL-трансформаций...")

    with psycopg.connect(
        **DB_CONFIG,
        password=password,
        autocommit=True,
    ) as conn:
        for filename in SQL_FILES:
            sql_path = SQL_DIR / filename

            if not sql_path.exists():
                raise FileNotFoundError(
                    f"SQL-файл не найден: {sql_path}"
                )

            print(f"Выполняется {filename}...")

            sql_text = sql_path.read_text(encoding="utf-8")
            conn.execute(sql_text)

            print(f"Готово: {filename}")

        # Этап 3. Проверка количества строк.
        print("\n[3/4] Проверка результатов...")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM clean.transactions"
            )
            clean_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM clean.transactions_typed"
            )
            typed_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM analytics.customer_summary"
            )
            customer_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) "
                "FROM analytics.transaction_quality_issues"
            )
            issue_count = cur.fetchone()[0]

        print(f"clean.transactions: {clean_count}")
        print(f"clean.transactions_typed: {typed_count}")
        print(f"analytics.customer_summary: {customer_count}")
        print(f"analytics.transaction_quality_issues: {issue_count}")

        if clean_count != typed_count:
            raise RuntimeError(
                "Количество строк в clean-таблицах не совпадает."
            )

        if customer_count == 0:
            raise RuntimeError(
                "Аналитическая сводка не содержит клиентов."
            )

    # Этап 4. Проверка качества данных.
    print("\n[4/4] Проверка качества данных...")

    subprocess.run(
        [sys.executable, str(QUALITY_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    print("\nETL PIPELINE ЗАВЕРШЁН УСПЕШНО.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nОШИБКА ETL: {exc}", file=sys.stderr)
        sys.exit(1)
