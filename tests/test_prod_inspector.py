import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import inspect_prod


class ProductionInspectorTests(unittest.TestCase):
    def test_rejects_any_project_other_than_the_known_production_project(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prod.env"
            path.write_text(
                "CUBEDBOT_PROD_SUPA_URL=https://wrong.supabase.co\n"
                "CUBEDBOT_PROD_SUPA_KEY=secret\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                inspect_prod.load_config(path)

    def test_inspector_uses_get_only(self):
        response = Mock()
        response.json.return_value = [{"id": 4, "data": {}}]
        response.raise_for_status = Mock()

        with (
            patch.object(
                inspect_prod,
                "load_config",
                return_value=(
                    "https://rcrhzlaartdajijumvlj.supabase.co",
                    "secret",
                ),
            ),
            patch.object(inspect_prod.requests, "get", return_value=response) as get,
        ):
            rows = inspect_prod.get_rows("vars", {"id": "eq.4"})

        self.assertEqual(rows[0]["id"], 4)
        get.assert_called_once()

    def test_nested_value_requires_an_exact_existing_path(self):
        self.assertEqual(
            inspect_prod.nested_value({"records": {"si": [1]}}, "records.si"),
            [1],
        )
        with self.assertRaises(KeyError):
            inspect_prod.nested_value({"records": {}}, "records.hr")


if __name__ == "__main__":
    unittest.main()
