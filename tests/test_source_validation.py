
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src import check_source_quality


class TestSourceValidation(unittest.TestCase):

    def setUp(self):
        # Создаём временную папку для тестовых CSV.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.raw_dir = Path(self.temp_dir.name)

        # Перенаправляем валидатор в тестовую папку.
        self.raw_dir_patcher = patch.object(
            check_source_quality,
            "RAW_DIR",
            self.raw_dir,
        )
        self.raw_dir_patcher.start()

        self.addCleanup(self.raw_dir_patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_missing_source_file(self):
        """Отсутствующий файл должен вызывать понятную ошибку."""

        with self.assertRaisesRegex(
            FileNotFoundError,
            "customers.csv",
        ):
            check_source_quality.load_source_file("customers.csv")

    def test_missing_required_column(self):
        """Отсутствие обязательной колонки должно выявляться."""

        file_path = self.raw_dir / "customers.csv"

        pd.DataFrame({
            "full_name": ["Test Customer"],
            "birth_date": ["1990-01-01"],
        }).to_csv(
            file_path,
            sep=";",
            index=False,
        )

        with self.assertRaisesRegex(
            ValueError,
            "customer_id",
        ):
            check_source_quality.load_source_file("customers.csv")

    def test_empty_source_file(self):
        """Пустой файл без заголовка должен вызывать ошибку."""

        file_path = self.raw_dir / "customers.csv"
        file_path.write_text("", encoding="utf-8")

        with self.assertRaisesRegex(
            ValueError,
            "customers.csv",
        ):
            check_source_quality.load_source_file("customers.csv")


if __name__ == "__main__":
    unittest.main()
