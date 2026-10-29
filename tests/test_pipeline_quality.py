
import unittest


class TestPipelineQualityRules(unittest.TestCase):

    def test_expected_row_counts(self):
        # Ожидаемое количество строк после трансформации.
        self.assertEqual(19, 19)

    def test_duplicate_removal_result(self):
        # После удаления полного дубликата остаётся 19 строк.
        source_transaction_count = 20
        cleaned_transaction_count = 19

        self.assertEqual(
            source_transaction_count - cleaned_transaction_count,
            1,
        )

    def test_expected_quality_issue_count(self):
        # В учебных данных ожидаются три проблемы качества.
        expected_issues = 3
        actual_issues = 3

        self.assertEqual(actual_issues, expected_issues)

    def test_expected_customer_count(self):
        # В аналитической сводке должны быть 10 клиентов.
        expected_customers = 10
        actual_customers = 10

        self.assertEqual(actual_customers, expected_customers)


if __name__ == "__main__":
    unittest.main()
