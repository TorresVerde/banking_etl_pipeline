from pathlib import Path
import logging
import os
import subprocess
import sys
from getpass import getpass

import psycopg


# ============================================================
# 1. Настройки проекта
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_DIR / "sql"
SRC_DIR = PROJECT_DIR / "src"

LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"

LOADER_SCRIPT = SRC_DIR / "load_to_staging.py"
SOURCE_QUALITY_SCRIPT = SRC_DIR / "check_source_quality.py"
PIPELINE_QUALITY_SCRIPT = SRC_DIR / "check_pipeline_quality.py"

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


# ============================================================
# 2. Настройка логирования
# ============================================================

def setup_logging():
    """Настраивает вывод сообщений в консоль и файл."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(
                LOG_FILE,
                encoding="utf-8",
            ),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


# ============================================================
# 3. Проверка наличия необходимых скриптов
# ============================================================

def validate_project_files():
    """Проверяет наличие скриптов и SQL-файлов."""

    required_files = [
        LOADER_SCRIPT,
        SOURCE_QUALITY_SCRIPT,
        PIPELINE_QUALITY_SCRIPT,
    ]

    required_files.extend(
        SQL_DIR / filename
        for filename in SQL_FILES
    )

    for file_path in required_files:
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Необходимый файл не найден: {file_path}"
            )

    logging.info("Все необходимые файлы проекта найдены.")


# ============================================================
# 4. Проверка исходных CSV
# ============================================================

def run_source_quality_checks(env):
    """
    Проверяет исходные CSV перед загрузкой в staging.

    Обнаруженные аномалии выводятся в отчёт.
    Сам скрипт check_source_quality.py пока не останавливает
    процесс при обнаружении дубликатов или нарушений связей.
    """

    logging.info("[1/5] Проверка исходных CSV-файлов...")

    subprocess.run(
        [sys.executable, str(SOURCE_QUALITY_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    logging.info("Проверка исходных CSV завершена.")


# ============================================================
# 5. Загрузка исходных данных
# ============================================================

def load_source_data(env):
    """Загружает исходные CSV-файлы в staging."""

    logging.info("[2/5] Загрузка исходных данных...")

    subprocess.run(
        [sys.executable, str(LOADER_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    logging.info("Загрузка исходных данных завершена.")


# ============================================================
# 6. SQL-трансформации и аналитика
# ============================================================

def execute_sql_files(conn):
    """Последовательно выполняет SQL-файлы проекта."""

    logging.info("[3/5] SQL-трансформации и аналитика...")

    for filename in SQL_FILES:
        sql_path = SQL_DIR / filename

        logging.info("Выполняется %s...", filename)

        sql_text = sql_path.read_text(encoding="utf-8")
        conn.execute(sql_text)

        logging.info("Файл %s выполнен успешно.", filename)


# ============================================================
# 7. Проверка результатов ETL
# ============================================================

def validate_pipeline_results(conn):
    """Проверяет базовые результаты ETL."""

    logging.info("[4/5] Проверка результатов ETL...")

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

    logging.info("clean.transactions: %s", clean_count)
    logging.info("clean.transactions_typed: %s", typed_count)
    logging.info("analytics.customer_summary: %s", customer_count)
    logging.info(
        "analytics.transaction_quality_issues: %s",
        issue_count,
    )

    if clean_count != typed_count:
        raise RuntimeError(
            "Количество строк в clean-таблицах не совпадает."
        )

    if customer_count == 0:
        raise RuntimeError(
            "Аналитическая сводка не содержит клиентов."
        )

    logging.info("Базовые проверки результатов пройдены.")


# ============================================================
# 8. Проверка качества обработанных данных
# ============================================================

def run_pipeline_quality_checks(env):
    """Запускает проверки качества результатов ETL."""

    logging.info("[5/5] Проверка качества обработанных данных...")

    subprocess.run(
        [sys.executable, str(PIPELINE_QUALITY_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    logging.info("Проверка качества обработанных данных завершена.")


# ============================================================
# 9. Основной процесс ETL
# ============================================================

def main():
    setup_logging()

    logging.info("=" * 60)
    logging.info("BANKING ETL PIPELINE: запуск")
    logging.info("=" * 60)

    validate_project_files()

    # Пароль не записывается в лог.
    password = os.environ.get("BANKING_ETL_DB_PASSWORD")

    if not password:
        password = getpass("Введите пароль PostgreSQL: ")

    env = os.environ.copy()
    env["BANKING_ETL_DB_PASSWORD"] = password

    # Этап 1. Проверяем исходные CSV.
    run_source_quality_checks(env)

    # Этап 2. Загружаем данные в staging.
    load_source_data(env)

    # Этапы 3 и 4. Преобразуем данные и проверяем результаты.
    logging.info("Подключение к базе данных PostgreSQL...")

    with psycopg.connect(
        **DB_CONFIG,
        password=password,
    ) as conn:
        execute_sql_files(conn)
        validate_pipeline_results(conn)

    # Этап 5. Проверяем качество обработанных данных.
    run_pipeline_quality_checks(env)

    logging.info("=" * 60)
    logging.info("BANKING ETL PIPELINE: успешно завершён")
    logging.info("Лог сохранён: %s", LOG_FILE)
    logging.info("=" * 60)


# ============================================================
# 10. Точка входа и обработка ошибок
# ============================================================

if __name__ == "__main__":
    try:
        main()

    except subprocess.CalledProcessError as exc:
        logging.error(
            "Дочерний скрипт завершился с ошибкой. Код: %s",
            exc.returncode,
        )
        sys.exit(1)

    except Exception:
        logging.exception("Ошибка выполнения ETL pipeline.")
        sys.exit(1)
