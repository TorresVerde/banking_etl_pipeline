
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"


class TestSourceFiles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.customers = pd.read_csv(
            RAW_DIR / "customers.csv",
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
        cls.accounts = pd.read_csv(
            RAW_DIR / "accounts.csv",
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
        cls.transactions = pd.read_csv(
            RAW_DIR / "transactions.csv",
            sep=";",
            dtype=str,
            keep_default_na=False,
        )

    def test_source_files_have_expected_columns(self):
        self.assertEqual(
            list(self.customers.columns),
            [
                "customer_id",
                "full_name",
                "birth_date",
                "registration_date",
                "customer_status",
            ],
        )

        self.assertEqual(
            list(self.accounts.columns),
            [
                "account_id",
                "customer_id",
                "account_type",
                "currency",
                "open_date",
                "account_status",
            ],
        )

        self.assertEqual(
            list(self.transactions.columns),
            [
                "transaction_id",
                "account_id",
                "transaction_ts",
                "amount",
                "currency",
                "operation_type",
                "transaction_status",
            ],
        )

    def test_source_ids_are_not_empty(self):
        for df, column in [
            (self.customers, "customer_id"),
            (self.accounts, "account_id"),
            (self.transactions, "transaction_id"),
        ]:
            with self.subTest(column=column):
                ids = df[column].str.strip()
                self.assertTrue(ids.ne("").all())

    def test_customer_and_account_ids_are_unique(self):
        self.assertTrue(
            self.customers["customer_id"].str.strip().is_unique
        )
        self.assertTrue(
            self.accounts["account_id"].str.strip().is_unique
        )

    def test_duplicate_transaction_is_detected(self):
        ids = self.transactions["transaction_id"].str.strip()
        duplicates = ids[ids.ne("")].duplicated().sum()

        self.assertEqual(duplicates, 1)
        self.assertEqual((ids == "T30014").sum(), 2)

    def test_accounts_reference_existing_customers(self):
        customer_ids = set(
            self.customers["customer_id"].str.strip()
        )

        account_customer_ids = set(
            self.accounts["customer_id"].str.strip()
        )

        self.assertTrue(
            account_customer_ids.issubset(customer_ids)
        )

    def test_missing_transaction_account_is_detected(self):
        account_ids = set(
            self.accounts["account_id"].str.strip()
        )

        invalid = self.transactions[
            ~self.transactions["account_id"]
            .str.strip()
            .isin(account_ids)
        ]

        self.assertEqual(len(invalid), 1)
        self.assertEqual(
            invalid.iloc[0]["transaction_id"],
            "T30011",
        )


if __name__ == "__main__":
    unittest.main()
