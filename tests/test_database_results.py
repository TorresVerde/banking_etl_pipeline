
import os
import unittest
from getpass import getpass

import psycopg


class TestDatabaseResults(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        password = os.environ.get("BANKING_ETL_DB_PASSWORD")

        if not password:
            password = getpass(
                "Введите пароль PostgreSQL для тестов: "
            )

        cls.conn = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="banking_dwh",
            user="etl_user",
            password=password,
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.conn.close()

    def get_count(self, query):
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]

    def test_clean_transactions_count(self):
        count = self.get_count(
            "SELECT COUNT(*) FROM clean.transactions"
        )
        self.assertEqual(count, 19)

    def test_typed_transactions_count(self):
        count = self.get_count(
            "SELECT COUNT(*) FROM clean.transactions_typed"
        )
        self.assertEqual(count, 19)

    def test_customer_summary_count(self):
        count = self.get_count(
            "SELECT COUNT(*) FROM analytics.customer_summary"
        )
        self.assertEqual(count, 10)

    def test_quality_issues_count(self):
        count = self.get_count(
            "SELECT COUNT(*) FROM analytics.transaction_quality_issues"
        )
        self.assertEqual(count, 3)

    def test_transaction_ids_are_not_empty(self):
        count = self.get_count("""
            SELECT COUNT(*)
            FROM clean.transactions_typed
            WHERE transaction_id IS NULL
               OR TRIM(transaction_id) = ''
        """)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
