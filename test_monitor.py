import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

import exchange_calendars as xc

from monitor import ET, archive, pair, prices_from_bars, session_info


class PriceScreenTests(unittest.TestCase):
    def setUp(self):
        self.calendar = xc.get_calendar("XNYS")
        self.day = "2026-11-09"

    def screen(self, low, close, today_low=None):
        today_low = low + 1 if today_low is None else today_low
        return prices_from_bars([
            {"t": "2026-11-06T05:00:00Z", "c": low + 2, "l": low, "h": low + 4},
            {"t": "2026-11-09T05:00:00Z", "c": close, "l": today_low, "h": close + 2},
        ], self.calendar, self.day)

    def test_dollar_only_inclusive(self):
        row = self.screen(50, 60)
        self.assertTrue(row["dollarTest"])
        self.assertFalse(row["percentTest"])
        self.assertTrue(row["qualified"])

    def test_percent_only_inclusive(self):
        row = self.screen(500, 550)
        self.assertFalse(row["dollarTest"])
        self.assertTrue(row["percentTest"])
        self.assertTrue(row["qualified"])

    def test_both_and_neither(self):
        self.assertTrue(self.screen(50, 54)["qualified"])
        self.assertFalse(self.screen(50, 61)["qualified"])

    def test_fresh_low_and_ties(self):
        row = self.screen(50, 48, 45)
        self.assertTrue(row["fresh"])
        self.assertEqual((row["low"], row["dollars"], row["lowDate"]), (45, 3, self.day))
        self.assertFalse(self.screen(50, 51, 50)["fresh"])

    def test_missing_latest_session_fails(self):
        with self.assertRaisesRegex(ValueError, "Missing current"):
            prices_from_bars([], self.calendar, self.day)

    def test_calendar_holiday_early_close_and_latest(self):
        def time(day, hour):
            return dt.datetime.fromisoformat(f"{day}T{hour}:00:00").replace(tzinfo=ET)
        self.assertIsNone(session_info(now=time("2026-11-26", "18")))
        self.assertEqual(session_info(now=time("2026-11-27", "14"))[1], "2026-11-27")
        with self.assertRaisesRegex(ValueError, "has not closed"):
            session_info(now=time("2026-11-27", "12"))
        self.assertEqual(session_info(now=time("2026-11-10", "10"), latest=True)[1], self.day)

    def test_archive_preserves_session_and_tracks_transitions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def report(day, values):
                return {"date": day, "rows": [{"ticker": ticker, "qualified": qualifying, "filings": []}
                                               for ticker, qualifying in values.items()]}
            archive(root, report("2026-11-06", {"A": True, "B": False}), self.calendar)
            archive(root, report(self.day, {"A": False, "B": True}), self.calendar)
            recent = json.loads((root / f"{self.day}.json").read_text())
            self.assertEqual(recent["new"], ["B"])
            self.assertEqual(recent["exited"], ["A"])
            self.assertEqual(json.loads((root / "index.json").read_text()), [self.day, "2026-11-06"])


class ResearchTests(unittest.TestCase):
    def test_annual_observations_exclude_quarters_and_later_amendments(self):
        def fact(start, end, value, filed, form="10-K"):
            return {"start": start, "end": end, "val": value, "filed": filed,
                    "form": form, "accn": filed + "-1"}
        facts = {"Revenue": {"units": {"USD": [
            fact("2024-01-01", "2024-12-31", 100, "2025-02-01"),
            fact("2025-01-01", "2025-12-31", 125, "2026-02-01"),
            fact("2026-01-01", "2026-03-31", 80, "2026-04-29", "10-Q"),
            fact("2025-01-01", "2025-12-31", 128, "2026-11-10", "10-K/A")
        ]}}}
        result = pair(facts, ["Revenue"], "2026-11-09")
        self.assertEqual(result["value"], 125)
        self.assertEqual(result["change"], 25)


if __name__ == "__main__":
    unittest.main()
