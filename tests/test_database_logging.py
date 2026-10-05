import io
import os
import sys
import unittest
import uuid
from unittest.mock import Mock, patch

import src.database_logging as database_logging
from src.database_logging import (
    DatabaseLogSink,
    TeeLogStream,
    database_logging_enabled,
    infer_level,
)


class FakeQuery:
    def __init__(self, calls, kind, payload=None):
        self.calls = calls
        self.kind = kind
        self.payload = payload

    def upsert(
        self,
        rows,
        on_conflict=None,
        ignore_duplicates=False,
        returning=None,
    ):
        self.calls.append((
            "upsert",
            rows,
            on_conflict,
            ignore_duplicates,
            returning,
        ))
        return self

    def execute(self):
        self.calls.append(("execute", self.kind))
        return {"data": []}


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return FakeQuery(self.calls, "table")

    def rpc(self, name):
        self.calls.append(("rpc", name))
        return FakeQuery(self.calls, "rpc")


class DatabaseLoggingTests(unittest.TestCase):
    def test_database_logging_is_enabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(database_logging_enabled())

    def test_database_logging_can_be_explicitly_disabled(self):
        with patch.dict(os.environ, {"DATABASE_LOGGING_ENABLED": "0"}, clear=True):
            self.assertFalse(database_logging_enabled())

    def test_level_is_derived_without_changing_message(self):
        self.assertEqual(infer_level("[ERROR] failed", "stdout"), "ERROR")
        self.assertEqual(infer_level("[WARN] retry", "stdout"), "WARN")
        self.assertEqual(infer_level("traceback line", "stderr"), "ERROR")
        self.assertEqual(infer_level("Loaded 20 cogs", "stdout"), "INFO")

    def test_tee_preserves_terminal_output_and_queues_complete_lines(self):
        original = io.StringIO()
        rows = []
        sink = type("Sink", (), {"enqueue": lambda _self, line, stream: rows.append((line, stream))})()
        stream = TeeLogStream(original, sink, "stdout")

        stream.write("first")
        stream.write(" line\nsecond line\n")

        self.assertEqual(original.getvalue(), "first line\nsecond line\n")
        self.assertEqual(rows, [
            ("first line", "stdout"),
            ("second line", "stdout"),
        ])

    def test_enqueued_rows_receive_stable_unique_ids(self):
        sink = DatabaseLogSink(FakeClient(), io.StringIO())

        sink.enqueue("hello", "stdout")
        sink.enqueue("again", "stdout")
        first = sink.queue.get_nowait()
        second = sink.queue.get_nowait()

        self.assertEqual(uuid.UUID(first["entry_id"]).version, 4)
        self.assertEqual(uuid.UUID(second["entry_id"]).version, 4)
        self.assertNotEqual(first["entry_id"], second["entry_id"])

    def test_sink_uses_idempotent_upsert_and_limited_prune_rpc(self):
        client = FakeClient()
        sink = DatabaseLogSink(client, io.StringIO())
        rows = [{"entry_id": "fixed-id", "message": "hello"}]

        sink._insert(rows)
        sink._insert(rows)
        sink._prune()

        self.assertIn(("table", "bot_logs"), client.calls)
        upserts = [call for call in client.calls if call[0] == "upsert"]
        self.assertEqual(upserts, [
            ("upsert", rows, "entry_id", True, "minimal"),
            ("upsert", rows, "entry_id", True, "minimal"),
        ])
        self.assertIn(("rpc", "prune_bot_logs"), client.calls)

    def test_installation_builds_a_dedicated_client(self):
        operational_client = FakeClient()
        logging_client = FakeClient()
        factory = Mock(return_value=logging_client)
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            with (
                patch.object(database_logging, "_installed_sink", None),
                patch.object(DatabaseLogSink, "start"),
                patch.object(database_logging.atexit, "register"),
            ):
                sink = database_logging.install_database_logging(
                    factory,
                    enabled=True,
                )

            factory.assert_called_once_with()
            self.assertIs(sink.client, logging_client)
            self.assertIsNot(sink.client, operational_client)
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_disabled_installation_does_not_build_a_client(self):
        factory = Mock()

        with patch.object(database_logging, "_installed_sink", None):
            sink = database_logging.install_database_logging(
                factory,
                enabled=False,
            )

        self.assertIsNone(sink)
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
