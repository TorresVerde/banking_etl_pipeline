
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
# 3. Загрузка исходных данных
# ============================================================

def load_source_data(env):
    """Запускает загрузку CSV-файлов в staging."""

    logging.info("[1/4] Загрузка исходных данных...")

    subprocess.run(
        [sys.executable, str(LOADER_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    logging.info("Загрузка исходных данных завершена.")


# ============================================================
# 4. SQL-трансформации и аналитика
# ============================================================

def execute_sql_files(conn):
    """Последовательно выполняет SQL-файлы проекта."""

    logging.info("[2/4] Выполнение SQL-трансформаций и аналитики...")

    for filename in SQL_FILES:
        sql_path = SQL_DIR / filename

        if not sql_path.exists():
            raise FileNotFoundError(
                f"SQL-файл не найден: {sql_path}"
            )

        logging.info("Выполняется %s...", filename)

        sql_text = sql_path.read_text(encoding="utf-8")

        conn.execute(sql_text)

        logging.info("Файл %s выполнен успешно.", filename)


# ============================================================
# 5. Проверка результатов ETL
# ============================================================

def validate_pipeline_results(conn):
    """Проверяет количество строк и базовую целостность результатов."""

    logging.info("[3/4] Проверка результатов ETL...")

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

    logging.info(
        "clean.transactions: %s",
        clean_count,
    )
    logging.info(
        "clean.transactions_typed: %s",
        typed_count,
    )
    logging.info(
        "analytics.customer_summary: %s",
        customer_count,
    )
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
# 6. Проверка качества данных
# ============================================================

def run_quality_checks(env):
    """Запускает отдельный скрипт проверок качества."""

    logging.info("[4/4] Проверка качества данных...")

    subprocess.run(
        [sys.executable, str(QUALITY_SCRIPT)],
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )

    logging.info("Проверка качества данных завершена успешно.")


# ============================================================
# 7. Основной процесс ETL
# ============================================================

def main():
    setup_logging()

    logging.info("=" * 55)
    logging.info("BANKING ETL PIPELINE: запуск")
    logging.info("=" * 55)

    if not LOADER_SCRIPT.exists():
        raise FileNotFoundError(
            f"Скрипт загрузки не найден: {LOADER_SCRIPT}"
        )

    if not QUALITY_SCRIPT.exists():
        raise FileNotFoundError(
            f"Скрипт проверки качества не найден: {QUALITY_SCRIPT}"
        )

    # Запрашиваем пароль один раз.
    # Пароль не записывается в лог.
    password = os.environ.get("BANKING_ETL_DB_PASSWORD")

    if not password:
        password = getpass("Введите пароль PostgreSQL: ")

    env = os.environ.copy()
    env["BANKING_ETL_DB_PASSWORD"] = password

    # Этап 1. Загружаем исходные CSV-файлы.
    load_source_data(env)

    # Этапы 2 и 3. Выполняем SQL и проверяем результаты.
    logging.info(
        "Подключение к базе данных PostgreSQL..."
    )

    with psycopg.connect(
        **DB_CONFIG,
        password=password,
    ) as conn:
        execute_sql_files(conn)
        validate_pipeline_results(conn)

    # Этап 4. Проверяем качество данных.
    run_quality_checks(env)

    logging.info("=" * 55)
    logging.info("BANKING ETL PIPELINE: успешно завершён")
    logging.info("Лог сохранён: %s", LOG_FILE)
    logging.info("=" * 55)


# ============================================================
# 8. Точка входа и обработка ошибок
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
