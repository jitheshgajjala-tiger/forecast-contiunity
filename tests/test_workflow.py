import unittest
from datetime import datetime, time, timezone
from unittest.mock import patch

from workflow import build_overwrite_statement, is_submission_open, validate_table_name


class WorkflowTests(unittest.TestCase):
    def test_schedule_requires_an_explicit_timebox(self):
        with patch.dict("os.environ", {"WINDOW_START": "CHANGE_ME", "WINDOW_END": "CHANGE_ME"}):
            from workflow import get_local_schedule

            with self.assertRaisesRegex(ValueError, "approved Tuesday timebox"):
                get_local_schedule()

    def test_submission_is_open_only_on_tuesday_inside_window(self):
        tuesday = datetime(2026, 10, 27, 10, 30, tzinfo=timezone.utc)
        monday = datetime(2026, 10, 26, 10, 30, tzinfo=timezone.utc)

        with patch("workflow.ZoneInfo", return_value=timezone.utc):
            self.assertTrue(is_submission_open(tuesday, time(10), time(11), "UTC")[0])
            self.assertFalse(is_submission_open(monday, time(10), time(11), "UTC")[0])

    def test_window_end_is_exclusive(self):
        at_end = datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc)
        with patch("workflow.ZoneInfo", return_value=timezone.utc):
            self.assertFalse(is_submission_open(at_end, time(10), time(11), "UTC")[0])

    def test_overwrite_includes_all_markets_and_a_utc_timestamp(self):
        statement = build_overwrite_statement(
            "main.forecast.business_signal_inputs",
            {"FR": True, "BE": False},
            "user@example.com",
            datetime(2026, 10, 27, 8, 30, tzinfo=timezone.utc),
        )

        self.assertIn("INSERT OVERWRITE TABLE main.forecast.business_signal_inputs", statement)
        self.assertIn("('FR', TRUE, 'user@example.com', TIMESTAMP '2026-10-27 08:30:00')", statement)
        self.assertIn("('BE', FALSE, 'user@example.com', TIMESTAMP '2026-10-27 08:30:00')", statement)

    def test_user_id_is_sql_escaped(self):
        statement = build_overwrite_statement(
            "main.forecast.business_signal_inputs",
            {"FR": True},
            "user'o@example.com",
            datetime(2026, 10, 27, 8, 30, tzinfo=timezone.utc),
        )
        self.assertIn("'user''o@example.com'", statement)

    def test_table_name_must_be_three_valid_parts(self):
        with self.assertRaises(ValueError):
            validate_table_name("main.forecast.inputs; DROP TABLE main.forecast.inputs")


if __name__ == "__main__":
    unittest.main()