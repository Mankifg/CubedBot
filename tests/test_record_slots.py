import copy
import unittest

from src import record_slots


def make_record(
    person_id="2021SREC01",
    country="SI",
    tag="NR",
    event_id="444",
    record_type="average",
    value=3000,
    competition_id="TestOpen2026",
):
    return {
        "type": record_type,
        "tag": tag,
        "attemptResult": value,
        "result": {
            "attempts": [],
            "person": {
                "name": "Test Competitor",
                "wcaId": person_id,
                "country": {"iso2": country, "name": country},
            },
            "round": {
                "id": 42,
                "competitionEvent": {
                    "event": {"id": event_id, "name": event_id},
                    "competition": {
                        "id": competition_id,
                        "wcaId": competition_id,
                        "name": "Test Open 2026",
                    },
                },
            },
        },
    }


class RecordSlotTests(unittest.TestCase):
    def test_schema_has_exactly_140_independent_slots(self):
        slots = record_slots.empty_record_slots()

        self.assertEqual(len(slots), 140)
        self.assertIn("WR:333:single", slots)
        self.assertIn("ER:fto:average", slots)
        self.assertIn("NR:SI:333mbf:single", slots)
        self.assertNotIn("NR:SI:333mbf:average", slots)

    def test_slovenian_world_record_is_copied_to_all_affected_slots(self):
        slots = record_slots.empty_record_slots()
        record = make_record(tag="WR", event_id="333", value=300)

        record_slots.record_delivery(
            slots,
            "si",
            record,
            "wca_live",
            sent_at="2026-10-05T10:00:00+00:00",
            message_id=123,
        )

        affected = [
            "WR:333:average",
            "ER:333:average",
            "NR:SI:333:average",
        ]
        for key in affected:
            self.assertEqual(len(slots[key]), 1)
            self.assertTrue(slots[key][0]["current"])
            self.assertEqual(
                slots[key][0]["deliveries"]["si"]["message_id"],
                "123",
            )
        self.assertEqual(slots["NR:HR:333:average"], [])

    def test_delivery_is_target_specific_across_highest_monikers(self):
        slots = record_slots.empty_record_slots()
        world = make_record(
            person_id="2024HRVA01",
            country="HR",
            tag="WR",
            event_id="444",
            value=1800,
        )
        national = copy.deepcopy(world)
        national["tag"] = "NR"

        record_slots.record_delivery(slots, "si", world, "wca_live")

        self.assertTrue(record_slots.already_delivered(slots, "si", national))
        self.assertFalse(record_slots.already_delivered(slots, "hr", national))

        record_slots.record_delivery(slots, "hr", national, "wca_official")

        self.assertTrue(record_slots.already_delivered(slots, "hr", national))
        for key in ("WR:444:average", "ER:444:average", "NR:HR:444:average"):
            self.assertIn("hr", slots[key][0]["deliveries"])

    def test_lower_level_seed_cannot_replace_higher_announced_moniker(self):
        slots = record_slots.empty_record_slots()
        world = make_record(tag="WR", event_id="333", value=300)
        european = copy.deepcopy(world)
        european["tag"] = "ER"

        record_slots.seed_record(
            slots,
            world,
            deliveries={"si": {"announced_as": "WR", "source": "wca_live"}},
            source="wca_live",
            current=True,
        )
        record_slots.seed_record(
            slots,
            european,
            deliveries={"si": {"announced_as": "ER", "source": "wca_official"}},
            source="wca_official",
            current=True,
        )

        for key in ("WR:333:average", "ER:333:average", "NR:SI:333:average"):
            self.assertEqual(
                slots[key][0]["deliveries"]["si"]["announced_as"],
                "WR",
            )

    def test_migration_propagates_historical_wr_when_country_was_unknown(self):
        slots = record_slots.empty_record_slots()
        legacy_world = make_record(tag="WR", country="", event_id="333oh", value=566)
        current_european = copy.deepcopy(legacy_world)
        current_european["tag"] = "ER"
        current_european["result"]["person"]["country"]["iso2"] = "CH"

        record_slots.seed_record(
            slots,
            legacy_world,
            deliveries={"si": {"announced_as": "WR", "source": None}},
            source=None,
        )
        record_slots.seed_record(
            slots,
            current_european,
            deliveries={"si": {"announced_as": "ER", "source": "wca_official"}},
            source="wca_official",
            current=True,
        )

        self.assertEqual(
            slots["ER:333oh:average"][0]["deliveries"]["si"]["announced_as"],
            "WR",
        )

    def test_equal_current_records_are_kept_as_ties(self):
        slots = record_slots.empty_record_slots()
        first = make_record(person_id="2021AAAA01", value=2500)
        second = make_record(
            person_id="2022BBBB01",
            value=2500,
            competition_id="OtherOpen2026",
        )

        record_slots.seed_record(slots, first, current=True)
        record_slots.seed_record(slots, second, current=True)

        entries = slots["NR:SI:444:average"]
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(entry["current"] for entry in entries))

    def test_better_record_replaces_current_but_preserves_history(self):
        slots = record_slots.empty_record_slots()
        old = make_record(person_id="2021AAAA01", value=2500)
        new = make_record(
            person_id="2022BBBB01",
            value=2400,
            competition_id="OtherOpen2026",
        )

        record_slots.seed_record(slots, old, current=True)
        record_slots.record_delivery(slots, "si", new, "cubing_china")

        entries = slots["NR:SI:444:average"]
        self.assertEqual(len(entries), 2)
        self.assertFalse(entries[0]["current"])
        self.assertTrue(entries[1]["current"])


if __name__ == "__main__":
    unittest.main()
