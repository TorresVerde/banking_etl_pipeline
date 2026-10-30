
from pathlib import Path

import pandas as pd


# ============================================================
# 1. Настройки проекта
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

# Проверяем только колонки, необходимые для текущих проверок.
REQUIRED_COLUMNS = {
    "customers.csv": {"customer_id"},
    "accounts.csv": {"account_id", "customer_id"},
    "transactions.csv": {"transaction_id", "account_id"},
}


# ============================================================
# 2. Загрузка и структурная проверка CSV
# ============================================================

def load_source_file(filename):
    """Проверяет файл и обязательные колонки, затем читает CSV."""

    file_path = RAW_DIR / filename

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Исходный CSV-файл не найден: {file_path}"
        )

    try:
        df = pd.read_csv(
            file_path,
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError(
            f"CSV-файл пуст или не содержит заголовка: {filename}"
        ) from exc
    except pd.errors.ParserError as exc:
        raise ValueError(
            f"Не удалось разобрать CSV-файл: {filename}. "
            f"Проверь разделитель и структуру строк."
        ) from exc

    # Убираем пробелы в названиях колонок.
    df.columns = df.columns.str.strip()

    required = REQUIRED_COLUMNS[filename]
    missing_columns = required - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"В файле {filename} отсутствуют обязательные "
            f"колонки: {', '.join(sorted(missing_columns))}"
        )

    print(
        f"[OK] {filename}: файл прочитан, "
        f"строк: {len(df)}, колонок: {len(df.columns)}"
    )

    return df


# ============================================================
# 3. Проверка идентификаторов
# ============================================================

def check_identifiers(datasets):
    """Показывает пустые и повторяющиеся идентификаторы."""

    print("\n=== КАЧЕСТВО ИСХОДНЫХ ДАННЫХ ===")

    for name, (df, id_column) in datasets.items():
        ids = df[id_column].str.strip()

        empty_count = ids.eq("").sum()

        # Пустые ID не считаем дубликатами.
        non_empty_ids = ids[ids.ne("")]
        duplicate_count = non_empty_ids.duplicated().sum()

        print(f"\nТаблица: {name}")
        print(f"Количество строк: {len(df)}")
        print(f"Пустые ID: {empty_count}")
        print(f"Дублирующиеся ID: {duplicate_count}")

        if empty_count:
            print(
                f"[WARNING] {name}: обнаружены пустые "
                f"значения в {id_column}."
            )

        if duplicate_count:
            print(
                f"[WARNING] {name}: обнаружены повторяющиеся "
                f"значения в {id_column}."
            )


# ============================================================
# 4. Проверка связей между таблицами
# ============================================================

def check_relationships(customers, accounts, transactions):
    """Проверяет ссылки счетов на клиентов и транзакций на счета."""

    customer_ids = set(customers["customer_id"].str.strip())
    customer_ids.discard("")

    account_ids = set(accounts["account_id"].str.strip())
    account_ids.discard("")

    account_customer_ids = accounts["customer_id"].str.strip()
    transaction_account_ids = transactions["account_id"].str.strip()

    invalid_account_customers = accounts[
        account_customer_ids.eq("")
        | ~account_customer_ids.isin(customer_ids)
    ]

    invalid_transaction_accounts = transactions[
        transaction_account_ids.eq("")
        | ~transaction_account_ids.isin(account_ids)
    ]

    print("\n=== ПРОВЕРКА СВЯЗЕЙ ===")
    print(
        "Счета с отсутствующим клиентом:",
        len(invalid_account_customers),
    )
    print(
        "Транзакции с отсутствующим счетом:",
        len(invalid_transaction_accounts),
    )

    if not invalid_account_customers.empty:
        print(
            "[WARNING] Обнаружены счета без корректной ссылки "
            "на клиента."
        )
        print(invalid_account_customers.to_string(index=False))

    if not invalid_transaction_accounts.empty:
        print(
            "[WARNING] Обнаружены транзакции без корректной "
            "ссылки на счёт."
        )
        print(invalid_transaction_accounts.to_string(index=False))


# ============================================================
# 5. Проверка дубликатов транзакций
# ============================================================

def check_transaction_duplicates(transactions):
    """Разделяет дубликаты ID и полные дубликаты строк."""

    print("\n=== ДУБЛИРУЮЩИЕСЯ ID ТРАНЗАКЦИЙ ===")

    transaction_ids = transactions["transaction_id"].str.strip()

    duplicate_id_mask = (
        transaction_ids.ne("")
        & transaction_ids.duplicated(keep=False)
    )

    if duplicate_id_mask.any():
        print(
            transactions.loc[duplicate_id_mask].to_string(
                index=False
            )
        )
    else:
        print("Повторяющихся ID транзакций нет.")

    print("\n=== ПОЛНЫЕ ДУБЛИКАТЫ СТРОК ===")

    full_duplicate_mask = transactions.duplicated(keep=False)
    full_duplicate_count = transactions.duplicated().sum()

    print(
        "Количество повторных копий полных строк:",
        full_duplicate_count,
    )

    if full_duplicate_mask.any():
        print(
            transactions.loc[full_duplicate_mask].to_string(
                index=False
            )
        )
    else:
        print("Полных дубликатов строк нет.")


# ============================================================
# 6. Основной процесс проверки исходных данных
# ============================================================

def main():
    print("=== ПРОВЕРКА ИСХОДНЫХ CSV-ФАЙЛОВ ===\n")

    customers = load_source_file("customers.csv")
    accounts = load_source_file("accounts.csv")
    transactions = load_source_file("transactions.csv")

    datasets = {
        "customers": (customers, "customer_id"),
        "accounts": (accounts, "account_id"),
        "transactions": (transactions, "transaction_id"),
    }

    check_identifiers(datasets)

    check_relationships(
        customers,
        accounts,
        transactions,
    )

    check_transaction_duplicates(transactions)

    print("\n=== ПРОВЕРКА ИСТОЧНИКОВ ЗАВЕРШЕНА ===")
    print(
        "Структурные проверки пройдены. "
        "Предупреждения о качестве требуют анализа."
    )


if __name__ == "__main__":
    main()
