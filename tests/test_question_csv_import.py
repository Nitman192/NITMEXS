import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.question_import_service import (
    CsvImportError,
    QuestionCsvImportService,
)
from phase1_server.services.question_service import QuestionService
from phase1_server.uow import UnitOfWork


class QuestionCsvImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "question_import.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _import(self, csv_content: str):
        with UnitOfWork(self.db) as uow:
            service = QuestionService(uow.questions)
            importer = QuestionCsvImportService(service)
            return importer.import_csv(csv_content)

    def test_valid_csv(self):
        csv_content = (
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "What is 2+2?,math,easy,1,3,false,4,true,5,false,6,false\n"
        )

        result = self._import(csv_content)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.failed, 0)

    def test_invalid_rows(self):
        csv_content = (
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "Bad question,math,easy,abc,3,false,4,true,,,\n"
            "Another question,math,easy,2,3,true,4,true,,,\n"
        )

        result = self._import(csv_content)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.errors[0].row, 2)
        self.assertIn("marks must be integer", result.errors[0].error)

    def test_partial_success(self):
        csv_content = (
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "Valid question,math,easy,2,3,false,4,true,5,false,6,false\n"
            "Invalid question,math,easy,2,3,true,4,true,,,\n"
        )

        result = self._import(csv_content)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.failed, 1)

    def test_empty_file(self):
        with self.assertRaises(CsvImportError):
            self._import("")


if __name__ == "__main__":
    unittest.main()
