
import os
import sys
from getpass import getpass

import psycopg


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "banking_dwh",
    "user": "etl_user",
}

EXPECTED_ISSUE_TYPES = {
    "MISSING_AMOUNT": 1,
    "ACCOUNT_NOT_FOUND": 1,
    "MISSING_OR_UNPARSED_DATE": 1,
}


def main():
    # Используем пароль из окружения, если его передал оркестратор.
    # При самостоятельном запуске запрашиваем пароль вручную.
    password = os.environ.get("BANKING_ETL_DB_PASSWORD")

    if not password:
        password = getpass("Введите пароль PostgreSQL: ")

    checks = []

    with psycopg.connect(
        **DB_CONFIG,
        password=password,
    ) as conn:
        with conn.cursor() as cur:

            # Проверка 1. Количество строк в clean-таблицах.
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM clean.transactions),
                    (SELECT COUNT(*) FROM clean.transactions_typed)
            """)
            raw_count, typed_count = cur.fetchone()

            checks.append((
                "Количество строк в clean-таблицах совпадает",
                raw_count == typed_count,
                f"transactions={raw_count}, typed={typed_count}",
            ))

            # Проверка 2. Полные дубликаты в clean.transactions.
            cur.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT
                        transaction_id,
                        account_id,
                        transaction_ts,
                        amount,
                        currency,
                        operation_type,
                        transaction_status
                    FROM clean.transactions
                    GROUP BY
                        transaction_id,
                        account_id,
                        transaction_ts,
                        amount,
                        currency,
                        operation_type,
                        transaction_status
                    HAVING COUNT(*) > 1
                ) AS duplicates
            """)
            duplicate_groups = cur.fetchone()[0]

            checks.append((
                "Полных дубликатов нет",
                duplicate_groups == 0,
                f"Групп дубликатов: {duplicate_groups}",
            ))

            # Проверка 3. Пустые идентификаторы транзакций.
            cur.execute("""
                SELECT COUNT(*)
                FROM clean.transactions_typed
                WHERE transaction_id IS NULL
                   OR TRIM(transaction_id) = ''
            """)
            empty_ids = cur.fetchone()[0]

            checks.append((
                "Нет пустых ID транзакций",
                empty_ids == 0,
                f"Пустых ID: {empty_ids}",
            ))

            # Проверка 4. Общее количество проблем качества.
            cur.execute("""
                SELECT COUNT(*)
                FROM analytics.transaction_quality_issues
            """)
            issue_count = cur.fetchone()[0]

            checks.append((
                "Количество проблем качества соответствует ожиданию",
                issue_count == sum(EXPECTED_ISSUE_TYPES.values()),
                (
                    f"Найдено проблем: {issue_count}, "
                    f"ожидалось: {sum(EXPECTED_ISSUE_TYPES.values())}"
                ),
            ))

            # Проверка 5. Конкретные типы проблем качества.
            cur.execute("""
                SELECT issue_type, COUNT(*)
                FROM analytics.transaction_quality_issues
                GROUP BY issue_type
            """)
            actual_issue_types = dict(cur.fetchall())

            checks.append((
                "Типы проблем качества соответствуют ожиданию",
                actual_issue_types == EXPECTED_ISSUE_TYPES,
                (
                    f"Найдено: {actual_issue_types}; "
                    f"ожидалось: {EXPECTED_ISSUE_TYPES}"
                ),
            ))

    print("\n=== ПРОВЕРКА КАЧЕСТВА ETL ===")

    failed = 0

    for name, passed, details in checks:
        status = "OK" if passed else "FAIL"
        print(f"[{status}] {name}: {details}")

        if not passed:
            failed += 1

    print(f"\nПроверок: {len(checks)}")
    print(f"Ошибок: {failed}")

    if failed:
        sys.exit(1)

    print("ПРОВЕРКА КАЧЕСТВА ЗАВЕРШЕНА УСПЕШНО.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ОШИБКА ПРОВЕРКИ: {exc}", file=sys.stderr)
        sys.exit(1)
