import unittest
from datetime import date

from src.cubing_china_records import (
    active_wca_competitions,
    live_result_to_records,
    trim_unentered_attempts,
)


class CubingChinaRecordsTests(unittest.TestCase):
    def test_active_competitions_require_live_wca_id_and_date_window(self):
        competitions = [
            {
                "alias": "active",
                "wcaCompetitionId": "Active2026",
                "live": True,
                "startDate": "2026-10-01",
                "endDate": "2026-10-03",
            },
            {
                "alias": "recent",
                "wcaCompetitionId": "Recent2026",
                "live": True,
                "startDate": "2026-09-30",
                "endDate": None,
            },
            {
                "alias": "unofficial",
                "wcaCompetitionId": "",
                "live": True,
                "startDate": "2026-10-02",
            },
            {
                "alias": "disabled",
                "wcaCompetitionId": "Disabled2026",
                "live": False,
                "startDate": "2026-10-02",
            },
        ]

        active = active_wca_competitions(competitions, date(2026, 10, 2))

        self.assertEqual([competition["alias"] for competition in active], [
            "active",
            "recent",
        ])

    def test_deqing_world_record_normalizes_to_existing_record_shape(self):
        competition = {
            "alias": "Deqing-Small-Special-2026",
            "wcaCompetitionId": "DeqingSmallSpecial2026",
            "name": "Deqing Small & Special 2026",
        }
        result = {
            "id": 386195,
            "competitionRoundId": 11361,
            "eventId": "333",
            "roundNumber": 3,
            "attempts": [379, 433, 361, 374, 280],
            "best": 280,
            "average": 371,
            "regionalSingleRecord": "AsR",
            "regionalAverageRecord": "WR",
            "competitor": {
                "name": "Xuanyi Geng",
                "localName": "耿暄一",
                "wcaId": "2023GENG02",
                "regionIso2": "CN",
            },
        }

        records = live_result_to_records(result, competition, "3x3x3 Cube")

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["type"], "average")
        self.assertEqual(record["attemptResult"], 371)
        self.assertEqual(record["result"]["person"]["name"], "Xuanyi Geng (耿暄一)")
        self.assertEqual(record["result"]["person"]["wcaId"], "2023GENG02")
        self.assertEqual(
            record["result"]["round"]["competitionEvent"]["competition"]["wcaId"],
            "DeqingSmallSpecial2026",
        )

    def test_trailing_unentered_attempts_are_removed(self):
        self.assertEqual(trim_unentered_attempts([18, 22, 20, 0, 0]), [18, 22, 20])
        self.assertEqual(trim_unentered_attempts([100, -1, -2]), [100, -1, -2])

    def test_single_and_average_world_records_share_the_same_result(self):
        competition = {
            "alias": "Beijing-Autumn-Rivalry-2026",
            "wcaCompetitionId": "BeijingAutumnRivalry2026",
            "name": "Beijing Autumn Rivalry 2026",
        }
        result = {
            "id": 410250,
            "competitionRoundId": 12026,
            "eventId": "777",
            "roundNumber": 2,
            "attempts": [9795, 8747, 10237],
            "best": 8747,
            "average": 9593,
            "regionalSingleRecord": "WR",
            "regionalAverageRecord": "WR",
            "competitor": {
                "name": "Timofei Tarasenko",
                "wcaId": "2019TARA09",
                "regionIso2": "RU",
            },
        }

        records = live_result_to_records(result, competition, "7x7x7 Cube")

        self.assertEqual([record["type"] for record in records], ["single", "average"])
        self.assertIs(records[0]["result"], records[1]["result"])

    def test_european_and_national_records_are_preserved(self):
        competition = {
            "alias": "Foreign-Records-2026",
            "wcaCompetitionId": "ForeignRecords2026",
            "name": "Foreign Records 2026",
        }
        european_result = {
            "id": 1,
            "eventId": "666",
            "attempts": [7000, 7100, 7200],
            "best": 7000,
            "average": 7100,
            "regionalSingleRecord": "NR",
            "regionalAverageRecord": "ER",
            "competitor": {
                "name": "European Competitor",
                "wcaId": "2026EURO01",
                "regionIso2": "SI",
            },
        }

        records = live_result_to_records(
            european_result,
            competition,
            "6x6x6 Cube",
        )

        self.assertEqual(
            [(record["type"], record["tag"]) for record in records],
            [("single", "NR"), ("average", "ER")],
        )

    def test_unmonitored_continental_records_are_ignored(self):
        competition = {
            "alias": "Asian-Records-2026",
            "wcaCompetitionId": "AsianRecords2026",
            "name": "Asian Records 2026",
        }
        result = {
            "id": 2,
            "eventId": "333",
            "attempts": [500, 600, 700, 800, 900],
            "best": 500,
            "average": 700,
            "regionalSingleRecord": "AsR",
            "regionalAverageRecord": "",
            "competitor": {
                "name": "Asian Competitor",
                "wcaId": "2026ASIA01",
                "regionIso2": "CN",
            },
        }

        self.assertEqual(
            live_result_to_records(result, competition, "3x3x3 Cube"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
