import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


def load_live_records_module():
    fake_wca = types.ModuleType("src.wca_function")
    fake_wca.c_data = []
    fake_wca.COUNTRIES_DICT = {}
    fake_db = types.ModuleType("src.db")
    fake_functions = types.ModuleType("src.functions")

    module_path = (
        Path(__file__).parents[1]
        / "src"
        / "Cogs"
        / "02_wca"
        / "06_live_records.py"
    )
    spec = importlib.util.spec_from_file_location("live_records_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "src.wca_function": fake_wca,
        "src.db": fake_db,
        "src.functions": fake_functions,
    }):
        spec.loader.exec_module(module)
    return module


LIVE_RECORDS = load_live_records_module()


def make_record(wca_id, tag="WR", record_type="average"):
    return {
        "type": record_type,
        "tag": tag,
        "attemptResult": 371,
        "result": {
            "attempts": [
                {"result": value}
                for value in [379, 433, 361, 374, 280]
            ],
            "person": {
                "name": "Xuanyi Geng (耿暄一)",
                "wcaId": wca_id,
                "country": {"iso2": "CN", "name": "China"},
            },
            "round": {
                "id": 11361,
                "competitionEvent": {
                    "event": {"id": "333", "name": "3x3x3 Cube"},
                    "competition": {
                        "id": "DeqingSmallSpecial2026",
                        "wcaId": "DeqingSmallSpecial2026",
                        "name": "Deqing Small & Special 2026",
                    },
                },
            },
        },
    }


class LiveRecordDedupeTests(unittest.TestCase):
    def test_existing_wca_id_canonical_key_is_unchanged(self):
        record = make_record("2023GENG02")

        self.assertEqual(
            LIVE_RECORDS.record_dedupe_key(record),
            "record:WR:333:average:2023GENG02:371:deqingsmallspecial2026",
        )

    def test_name_alias_blocks_later_official_wca_id_duplicate(self):
        live_record = make_record("")
        official_record = make_record("2023GENG02")
        dedupe_map = {"wr": []}
        pending_map = {"wr": {}}

        LIVE_RECORDS.mark_pending_record(
            pending_map,
            "wr",
            live_record,
            "cubing_china",
        )
        self.assertTrue(
            LIVE_RECORDS.already_sent_record(
                dedupe_map,
                pending_map,
                "wr",
                official_record,
            )
        )

        LIVE_RECORDS.clear_pending_record(pending_map, "wr", live_record)
        LIVE_RECORDS.mark_sent_record(dedupe_map, "wr", live_record)
        self.assertTrue(
            LIVE_RECORDS.already_sent_record(
                dedupe_map,
                pending_map,
                "wr",
                official_record,
            )
        )

    def test_higher_record_moniker_blocks_later_lower_level_duplicates(self):
        world_record = make_record("2023GENG02", tag="WR")
        european_record = make_record("2023GENG02", tag="ER")
        national_record = make_record("2023GENG02", tag="NR")
        dedupe_map = {"records": []}
        pending_map = {"records": {}}

        LIVE_RECORDS.mark_sent_record(dedupe_map, "records", world_record)

        self.assertTrue(
            LIVE_RECORDS.already_sent_record(
                dedupe_map,
                pending_map,
                "records",
                european_record,
            )
        )
        self.assertTrue(
            LIVE_RECORDS.already_sent_record(
                dedupe_map,
                pending_map,
                "records",
                national_record,
            )
        )

    def test_same_person_single_and_average_share_one_message_batch(self):
        single = make_record("2023GENG02", record_type="single")
        average = make_record("2023GENG02", record_type="average")

        batches = LIVE_RECORDS.grouped_record_batches([single, average])

        self.assertEqual(batches, [[average, single]])
        self.assertNotEqual(
            LIVE_RECORDS.record_dedupe_key(single),
            LIVE_RECORDS.record_dedupe_key(average),
        )

    def test_different_people_remain_separate_message_batches(self):
        single = make_record("2023GENG02", record_type="single")
        average = make_record("2019TARA09", record_type="average")

        batches = LIVE_RECORDS.grouped_record_batches([single, average])

        self.assertEqual(batches, [[single], [average]])


class CubingChinaEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_revision_gap_processes_upserts_and_reconciles_snapshot(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.cubing_china_round_revisions = {}
        cog._process_cubing_china_results = AsyncMock()
        cog._fetch_cubing_china_snapshot = AsyncMock()
        result = {"id": 1, "eventId": "333"}

        await cog._handle_cubing_china_event(
            "test-competition",
            '{"type":"result.updated","payload":{"round":{"id":9,'
            '"revision":1},"upsertedResults":[{"id":1,"eventId":"333"}],'
            '"removedResultIds":[]}}',
        )
        await cog._handle_cubing_china_event(
            "test-competition",
            '{"type":"result.updated","payload":{"round":{"id":9,'
            '"revision":3},"upsertedResults":[{"id":1,"eventId":"333"}],'
            '"removedResultIds":[]}}',
        )

        self.assertEqual(cog._process_cubing_china_results.await_count, 2)
        cog._process_cubing_china_results.assert_awaited_with(
            "test-competition",
            [result],
        )
        cog._fetch_cubing_china_snapshot.assert_awaited_once_with(
            "test-competition"
        )


if __name__ == "__main__":
    unittest.main()
