
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"


def main():
    # 1. Загружаем исходные CSV-файлы
    customers = pd.read_csv(
        RAW_DIR / "customers.csv",
        sep=";",
        dtype=str,
        keep_default_na=False,
    )
    accounts = pd.read_csv(
        RAW_DIR / "accounts.csv",
        sep=";",
        dtype=str,
        keep_default_na=False,
    )
    transactions = pd.read_csv(
        RAW_DIR / "transactions.csv",
        sep=";",
        dtype=str,
        keep_default_na=False,
    )

    # 2. Проверяем количество строк, пустые ID и дубликаты
    datasets = {
        "customers": (customers, "customer_id"),
        "accounts": (accounts, "account_id"),
        "transactions": (transactions, "transaction_id"),
    }

    print("=== КАЧЕСТВО ИСХОДНЫХ ДАННЫХ ===")

    for name, (df, id_column) in datasets.items():
        ids = df[id_column].str.strip()

        print(f"\nТаблица: {name}")
        print(f"Количество строк: {len(df)}")
        print(f"Пустые ID: {(ids == '').sum()}")
        print(
            f"Дублирующиеся ID: "
            f"{ids[ids != ''].duplicated().sum()}"
        )

    # 3. Проверяем связи между клиентами и счетами
    customer_ids = set(customers["customer_id"].str.strip())
    customer_ids.discard("")

    account_ids = set(accounts["account_id"].str.strip())
    account_ids.discard("")

    invalid_account_customers = accounts[
        ~accounts["customer_id"].str.strip().isin(customer_ids)
    ]

    invalid_transaction_accounts = transactions[
        ~transactions["account_id"].str.strip().isin(account_ids)
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

    # 4. Показываем конкретные дублирующиеся транзакции
    print("\n=== ДУБЛИРУЮЩИЕСЯ ТРАНЗАКЦИИ ===")

    transaction_ids = transactions["transaction_id"].str.strip()

    duplicate_mask = (
        transaction_ids.ne("")
        & transaction_ids.duplicated(keep=False)
    )

    if duplicate_mask.any():
        print(
            transactions.loc[duplicate_mask].to_string(index=False)
        )
    else:
        print("Дубликатов нет")

    # 5. Показываем транзакции с неизвестным счетом
    print("\n=== ТРАНЗАКЦИИ С НЕИЗВЕСТНЫМ СЧЁТОМ ===")

    if not invalid_transaction_accounts.empty:
        print(invalid_transaction_accounts.to_string(index=False))
    else:
        print("Проблемных записей нет")


if __name__ == "__main__":
    main()
