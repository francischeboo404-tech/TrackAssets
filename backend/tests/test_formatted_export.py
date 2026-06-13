import csv
import io
import unittest

from app.utils.formatted_export import (
    CSV_BOM,
    TRACKIT_BRAND,
    build_csv_document,
    build_csv_multi_section,
)


class TestFormattedExport(unittest.TestCase):
    def test_csv_document_has_metadata_then_headers_then_data(self):
        content = build_csv_document(
            "Test Asset Register",
            "Acme Corp",
            ["Code", "Name", "Value"],
            [["A-1", "Laptop", "1000"]],
            subtitle="Sample subtitle",
        )

        self.assertTrue(content.startswith(CSV_BOM))
        reader = csv.reader(io.StringIO(content.lstrip(CSV_BOM)))
        rows = list(reader)

        self.assertEqual(rows[0][0], TRACKIT_BRAND)
        self.assertEqual(rows[1][0], "Test Asset Register")
        self.assertIn("Acme Corp", rows[2][0])

        header_idx = next(
            i for i, r in enumerate(rows) if r == ["Code", "Name", "Value"]
        )
        self.assertGreater(header_idx, 3)
        self.assertEqual(rows[header_idx + 1], ["A-1", "Laptop", "1000"])

    def test_csv_multi_section_inserts_section_titles(self):
        content = build_csv_multi_section(
            "Full Export",
            "Acme Corp",
            [
                {
                    "title": "Assets",
                    "headers": ["Code"],
                    "rows": [["X1"]],
                },
                {
                    "title": "Inventory",
                    "headers": ["SKU"],
                    "rows": [["SKU-1"]],
                },
            ],
        )

        self.assertIn("Assets", content)
        self.assertIn("Inventory", content)
        self.assertIn("SKU-1", content)
        self.assertIn("X1", content)


if __name__ == "__main__":
    unittest.main()
