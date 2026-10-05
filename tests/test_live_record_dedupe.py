import asyncio
import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


def load_live_records_module():
    fake_wca = types.ModuleType("src.wca_function")
    fake_wca.c_data = []
    fake_wca.COUNTRIES_DICT = {}
    fake_db = types.ModuleType("src.db")
    fake_functions = types.ModuleType("src.functions")
    fake_guild_access = types.ModuleType("src.guild_access")
    fake_guild_access.primary_guild_ids = lambda: [123]
    fake_guild_access.ensure_primary_guild = AsyncMock(return_value=True)

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
        "src.guild_access": fake_guild_access,
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

    def test_unchanged_candidate_is_confirmed_only_after_delay(self):
        record = make_record("2023GENG02")

        confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
            [record], {}, 100, 180,
        )
        self.assertEqual(confirmed, [])

        confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
            [record], state, 279, 180,
        )
        self.assertEqual(confirmed, [])

        confirmed, _state = LIVE_RECORDS.reconcile_record_confirmations(
            [record], state, 280, 180,
        )
        self.assertEqual(confirmed, [[record]])

    def test_confirmed_single_and_average_stay_grouped(self):
        single = make_record("2023GENG02", record_type="single")
        average = make_record("2023GENG02", record_type="average")

        _confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
            [single, average], {}, 0, 180,
        )
        confirmed, _state = LIVE_RECORDS.reconcile_record_confirmations(
            [single, average], state, 180, 180,
        )

        self.assertEqual(confirmed, [[average, single]])

    def test_confirmed_candidate_change_restarts_delay(self):
        original = make_record("2019WUJU07", record_type="single")
        original["attemptResult"] = 232
        corrected = copy.deepcopy(original)
        corrected["attemptResult"] = 1752

        _confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
            [original], {}, 0, 180,
        )
        confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
            [corrected], state, 180, 180,
        )
        self.assertEqual(confirmed, [])

        confirmed, _state = LIVE_RECORDS.reconcile_record_confirmations(
            [corrected], state, 360, 180,
        )
        self.assertEqual(confirmed, [[corrected]])

    def test_production_false_candidates_disappear_without_confirmation(self):
        false_records = []
        for person_id, person_name, event_id, tag, record_type, value in (
            ("2019WUJU07", "Junyuan Wu", "333", "WR", "single", 232),
            ("2019WUJU07", "Junyuan Wu", "333", "WR", "single", 1752),
            ("2019TARA09", "Timofei Tarasenko", "clock", "ER", "average", 513),
            ("2019TARA09", "Timofei Tarasenko", "clock", "ER", "average", 587),
        ):
            record = make_record(person_id, tag=tag, record_type=record_type)
            record["attemptResult"] = value
            record["result"]["person"]["name"] = person_name
            record["result"]["round"]["competitionEvent"]["event"] = {
                "id": event_id,
                "name": LIVE_RECORDS.event_display_name(event_id),
            }
            record["result"]["round"]["competitionEvent"]["competition"] = {
                "id": "GuangzhouGrandOpen2026",
                "wcaId": "GuangzhouGrandOpen2026",
                "name": "Guangzhou Grand Open 2026",
            }
            false_records.append(record)

        self.assertEqual(
            {
                key
                for record in false_records
                for key in LIVE_RECORDS.record_canonical_keys(record)
            },
            {
                "record:WR:333:single:2019WUJU07:232:guangzhougrandopen2026",
                "record:WR:333:single:name-junyuanwu:232:guangzhougrandopen2026",
                "record:WR:333:single:2019WUJU07:1752:guangzhougrandopen2026",
                "record:WR:333:single:name-junyuanwu:1752:guangzhougrandopen2026",
                "record:ER:clock:average:2019TARA09:513:guangzhougrandopen2026",
                "record:ER:clock:average:name-timofeitarasenko:513:guangzhougrandopen2026",
                "record:ER:clock:average:2019TARA09:587:guangzhougrandopen2026",
                "record:ER:clock:average:name-timofeitarasenko:587:guangzhougrandopen2026",
            },
        )

        for record in false_records:
            confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
                [record], {}, 0, 180,
            )
            self.assertEqual(confirmed, [])
            confirmed, state = LIVE_RECORDS.reconcile_record_confirmations(
                [], state, 180, 180,
            )
            self.assertEqual(confirmed, [])
            self.assertEqual(state, {})


class RecordSourceLinkTests(unittest.TestCase):
    def test_wca_live_links_directly_to_round(self):
        record = make_record("2023GENG02")
        record["result"]["round"]["competitionEvent"]["competition"]["id"] = 42

        self.assertEqual(
            LIVE_RECORDS.record_competition_url(record, "wca_live"),
            "https://live.worldcubeassociation.org/competitions/42/rounds/11361",
        )
        with (
            patch.object(
                LIVE_RECORDS.functions,
                "convert_to_human_frm",
                return_value="3.71",
                create=True,
            ),
            patch.object(
                LIVE_RECORDS.functions,
                "avg_of",
                return_value=371,
                create=True,
            ),
        ):
            embed = LIVE_RECORDS.build_record_embed(record, source="wca_live")
        self.assertIn(
            "[Deqing Small & Special 2026](https://live.worldcubeassociation.org/competitions/42/rounds/11361)",
            embed.fields[1].value,
        )

    def test_cubing_china_links_directly_to_live_round(self):
        record = make_record("2023GENG02")
        competition = record["result"]["round"]["competitionEvent"]["competition"]
        competition["cubingChinaAlias"] = "Deqing-Small-Special-2026"
        record["result"]["round"]["number"] = 3

        self.assertEqual(
            LIVE_RECORDS.record_competition_url(record, "cubing_china"),
            "https://cubing.com/competition/Deqing-Small-Special-2026/live?eventId=333&roundNumber=3",
        )

    def test_official_links_to_record_level_page(self):
        world = make_record("2023GENG02", tag="WR")
        europe = make_record("2019TARA09", tag="ER")
        national = make_record("2021SREC01", tag="NR")
        national["result"]["person"]["country"] = {
            "iso2": "SI",
            "name": "Slovenia",
        }

        self.assertEqual(
            LIVE_RECORDS.record_competition_url(world, "wca_official"),
            "https://www.worldcubeassociation.org/results/records?region=World&show=mixed",
        )
        self.assertEqual(
            LIVE_RECORDS.record_competition_url(europe, "wca_official"),
            "https://www.worldcubeassociation.org/results/records?region=_Europe&show=mixed",
        )
        self.assertEqual(
            LIVE_RECORDS.record_competition_url(national, "wca_official"),
            "https://www.worldcubeassociation.org/results/records?region=Slovenia&show=mixed",
        )

    def test_link_metadata_does_not_change_canonical_identity(self):
        record = make_record("2023GENG02")
        key = LIVE_RECORDS.record_dedupe_key(record)
        competition = record["result"]["round"]["competitionEvent"]["competition"]
        competition["cubingChinaAlias"] = "Deqing-Small-Special-2026"
        record["result"]["round"]["number"] = 3

        self.assertEqual(LIVE_RECORDS.record_dedupe_key(record), key)


class CubingChinaEventTests(unittest.IsolatedAsyncioTestCase):
    def test_stable_stream_disconnect_reconnects_without_warning(self):
        self.assertEqual(
            LIVE_RECORDS.cubing_china_stream_failure_state(4, 60),
            (0, False),
        )

    def test_short_stream_failures_warn_first_and_every_fifth_time(self):
        failures = 0
        warnings = []
        for _ in range(10):
            failures, should_warn = (
                LIVE_RECORDS.cubing_china_stream_failure_state(failures, 10)
            )
            if should_warn:
                warnings.append(failures)

        self.assertEqual(warnings, [1, 5, 10])

    async def test_sse_upserts_only_trigger_authoritative_snapshot(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.cubing_china_round_revisions = {}
        cog.cubing_china_etags = {"test-competition": "old-etag"}
        cog._process_cubing_china_results = AsyncMock()
        cog._fetch_cubing_china_snapshot = AsyncMock()

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

        cog._process_cubing_china_results.assert_not_awaited()
        self.assertEqual(cog._fetch_cubing_china_snapshot.await_count, 2)
        self.assertNotIn("test-competition", cog.cubing_china_etags)

    async def test_snapshot_candidate_must_survive_three_minutes(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.record_source_states = dict(LIVE_RECORDS.RECORD_SOURCE_DEFAULTS)
        cog.cubing_china_competitions = {
            "test-competition": {
                "alias": "Test-Competition-2026",
                "wcaCompetitionId": "TestCompetition2026",
                "name": "Test Competition 2026",
            },
        }
        cog.cubing_china_confirmations = {}
        cog.records_check_lock = asyncio.Lock()
        cog._process_wca_live_records = AsyncMock()
        result = {
            "id": 1,
            "competitionRoundId": 9,
            "eventId": "333",
            "roundNumber": 1,
            "attempts": [500, 600, 700, 800, 900],
            "best": 500,
            "average": 700,
            "regionalSingleRecord": "WR",
            "regionalAverageRecord": "",
            "competitor": {
                "name": "Stable Competitor",
                "wcaId": "2026STAB01",
                "regionIso2": "SI",
            },
        }

        with (
            patch.object(
                LIVE_RECORDS,
                "time",
                types.SimpleNamespace(monotonic=Mock(side_effect=[0, 180])),
            ),
            patch.object(
                LIVE_RECORDS,
                "load_live_record_targets",
                return_value=[{"key": "si"}],
            ),
            patch.object(
                LIVE_RECORDS,
                "load_live_record_dedupe_row",
                return_value={"data": {}},
            ),
        ):
            await cog._process_cubing_china_results(
                "test-competition",
                [result],
            )
            cog._process_wca_live_records.assert_not_awaited()

            await cog._process_cubing_china_results(
                "test-competition",
                [result],
            )

        cog._process_wca_live_records.assert_awaited_once()
        self.assertEqual(
            cog._process_wca_live_records.await_args.kwargs["source"],
            "cubing_china",
        )

    async def test_etag_304_revalidates_cached_snapshot_for_confirmation(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.cubing_china_etags = {"test-competition": '"etag-1"'}
        cached_results = [{"id": 1, "eventId": "333"}]
        cog.cubing_china_snapshot_cache = {
            "test-competition": cached_results,
        }
        cog.cubing_china_snapshot_locks = {}
        cog._process_cubing_china_results = AsyncMock()

        response = AsyncMock()
        response.status = 304
        response_context = AsyncMock()
        response_context.__aenter__.return_value = response
        session = types.SimpleNamespace(
            get=Mock(return_value=response_context),
        )
        cog._ensure_cubing_china_session = AsyncMock(return_value=session)

        await cog._fetch_cubing_china_snapshot("test-competition")

        request_headers = session.get.call_args.kwargs["headers"]
        self.assertEqual(request_headers, {"If-None-Match": '"etag-1"'})
        cog._process_cubing_china_results.assert_awaited_once_with(
            "test-competition",
            cached_results,
        )


class RecordSourceControlTests(unittest.IsolatedAsyncioTestCase):
    def test_wca_live_polls_every_five_minutes(self):
        self.assertEqual(
            LIVE_RECORDS.liveRecordsCog.wca_live_check.seconds,
            300,
        )

    async def test_wca_live_rechecks_candidate_after_three_minutes(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.wca_live_confirmations = {}
        cog._fetch_wca_live_records = Mock(
            return_value=[make_record("2023GENG02")]
        )
        cog._process_wca_live_records = AsyncMock()
        cog._schedule_wca_live_confirmation = Mock()

        with (
            patch.object(
                LIVE_RECORDS,
                "time",
                types.SimpleNamespace(monotonic=Mock(side_effect=[0, 180])),
            ),
            patch.object(
                LIVE_RECORDS,
                "load_live_record_targets",
                return_value=[{"key": "si"}],
            ),
            patch.object(
                LIVE_RECORDS,
                "load_live_record_dedupe_row",
                return_value={"data": {}},
            ),
        ):
            await cog._wca_live_check()
            cog._process_wca_live_records.assert_not_awaited()

            await cog._wca_live_check()

        cog._process_wca_live_records.assert_awaited_once()
        self.assertEqual(cog._fetch_wca_live_records.call_count, 2)

    def test_missing_or_invalid_source_settings_default_to_enabled(self):
        self.assertEqual(
            LIVE_RECORDS.normalize_record_source_states({}),
            LIVE_RECORDS.RECORD_SOURCE_DEFAULTS,
        )
        self.assertEqual(
            LIVE_RECORDS.normalize_record_source_states({
                "record_sources": {
                    "wca_live": False,
                    "cubing_china": "false",
                },
            }),
            {
                "wca_live": False,
                "cubing_china": True,
                "wca_official": True,
            },
        )

    def test_save_source_setting_preserves_record_target_configuration(self):
        row = {
            "id": 3,
            "data": {
                "records_targets": [{"key": "si"}],
                "record_sources": {"wca_live": False},
            },
        }
        LIVE_RECORDS.db.load_second_table_idd = Mock(return_value=row)
        LIVE_RECORDS.db.save_second_table_idd = Mock()

        states = LIVE_RECORDS.save_record_source_state("cubing_china", False)

        self.assertEqual(row["data"]["records_targets"], [{"key": "si"}])
        self.assertEqual(states, {
            "wca_live": False,
            "cubing_china": False,
            "wca_official": True,
        })
        LIVE_RECORDS.db.save_second_table_idd.assert_called_once_with(row)

    def test_all_updates_every_source_in_one_database_save(self):
        row = {
            "id": 3,
            "data": {
                "records_targets": [{"key": "si"}],
                "record_sources": {"wca_live": False},
            },
        }
        LIVE_RECORDS.db.load_second_table_idd = Mock(return_value=row)
        LIVE_RECORDS.db.save_second_table_idd = Mock()

        states = LIVE_RECORDS.save_record_source_state("all", True)

        self.assertEqual(states, {
            "wca_live": True,
            "cubing_china": True,
            "wca_official": True,
        })
        self.assertEqual(row["data"]["records_targets"], [{"key": "si"}])
        LIVE_RECORDS.db.save_second_table_idd.assert_called_once_with(row)

    def test_only_configured_user_can_control_sources(self):
        owner = types.SimpleNamespace(id=697176514676129933, roles=[])
        second_owner = types.SimpleNamespace(id=732917883591589920, roles=[])
        other = types.SimpleNamespace(id=1, roles=[])

        self.assertTrue(LIVE_RECORDS.can_control_record_sources(owner))
        self.assertTrue(LIVE_RECORDS.can_control_record_sources(second_owner))
        self.assertFalse(LIVE_RECORDS.can_control_record_sources(other))

    def test_command_choices_and_status_use_requested_labels(self):
        command = LIVE_RECORDS.liveRecordsCog.recordsource
        source_option = next(option for option in command.options if option.name == "source")
        state_option = next(option for option in command.options if option.name == "state")

        self.assertEqual(
            [(choice.name, choice.value) for choice in source_option.choices],
            [
                ("All", "all"),
                ("WCA Live", "wca_live"),
                ("Cubing China", "cubing_china"),
                ("WCA Official", "wca_official"),
            ],
        )
        self.assertEqual(
            [(choice.name, choice.value) for choice in state_option.choices],
            [("On", "on"), ("Off", "off")],
        )
        self.assertEqual(command.guild_ids, [123])

        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.record_source_states = dict(LIVE_RECORDS.RECORD_SOURCE_DEFAULTS)
        self.assertEqual(
            cog._record_source_status_text(),
            "**WCA Live:** On\n**Cubing China:** On\n**WCA Official:** On",
        )

    def test_recordsources_command_is_removed(self):
        self.assertFalse(hasattr(LIVE_RECORDS.liveRecordsCog, "recordsources"))

    async def test_authorized_command_defers_publicly_before_database_work(self):
        events = []
        ctx = types.SimpleNamespace(
            guild_id=123,
            author=types.SimpleNamespace(id=697176514676129933, roles=[]),
            defer=AsyncMock(
                side_effect=lambda **_kwargs: events.append("defer")
            ),
            edit=AsyncMock(
                side_effect=lambda **_kwargs: events.append("edit")
            ),
            respond=AsyncMock(),
        )
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.bot = types.SimpleNamespace(loop=types.SimpleNamespace(create_task=Mock()))
        cog.records_check_lock = asyncio.Lock()
        cog.record_source_states = dict(LIVE_RECORDS.RECORD_SOURCE_DEFAULTS)
        cog.wca_live_confirmations = {}
        cog.wca_live_confirmation_task = None

        def save_source(source, enabled):
            events.append("save")
            states = dict(LIVE_RECORDS.RECORD_SOURCE_DEFAULTS)
            states[source] = enabled
            return states

        with (
            patch.object(LIVE_RECORDS, "RECORD_SOURCE_GUILD_IDS", [123]),
            patch.object(
                LIVE_RECORDS,
                "save_record_source_state",
                side_effect=save_source,
            ),
        ):
            await LIVE_RECORDS.liveRecordsCog.recordsource.callback(
                cog,
                ctx,
                "wca_live",
                "off",
            )

        self.assertEqual(events, ["defer", "save", "edit"])
        ctx.defer.assert_awaited_once_with(ephemeral=False)
        response = ctx.edit.await_args.kwargs["content"]
        self.assertIn("**WCA Live:** Off", response)
        self.assertNotIn("enabled", response)
        self.assertNotIn("disabled", response)

    async def test_disabled_source_skips_immediate_check(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.records_check_lock = asyncio.Lock()
        cog.record_source_states = dict(LIVE_RECORDS.RECORD_SOURCE_DEFAULTS)
        cog.record_source_states["wca_live"] = False
        cog._wca_live_check = AsyncMock()

        await cog._run_enabled_record_source_once("wca_live")

        cog._wca_live_check.assert_not_awaited()

    async def test_enabled_source_runs_immediate_check(self):
        cog = object.__new__(LIVE_RECORDS.liveRecordsCog)
        cog.records_check_lock = asyncio.Lock()
        cog.record_source_states = dict(LIVE_RECORDS.RECORD_SOURCE_DEFAULTS)
        cog._wca_live_check = AsyncMock()

        await cog._run_enabled_record_source_once("wca_live")

        cog._wca_live_check.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
