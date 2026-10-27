import re
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_MARKETS = ("FR", "BE", "NL", "SE", "IS", "DK", "GB", "IE", "PL")
IDENTIFIER_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MARKET_CODE = re.compile(r"^[A-Z0-9_-]+$")


def get_local_schedule() -> tuple[time, time, str]:
    import os

    timezone_name = os.getenv("BUSINESS_TIMEZONE", "Europe/Brussels")
    raw_start = os.getenv("WINDOW_START", "")
    raw_end = os.getenv("WINDOW_END", "")
    if not raw_start or not raw_end or "CHANGE_ME" in raw_start + raw_end:
        raise ValueError("Set WINDOW_START and WINDOW_END to the approved Tuesday timebox")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone {timezone_name!r}") from exc

    start_time = _parse_time(raw_start, "WINDOW_START")
    end_time = _parse_time(raw_end, "WINDOW_END")
    if start_time >= end_time:
        raise ValueError("WINDOW_START must be earlier than WINDOW_END on the same day")
    return start_time, end_time, timezone_name


def _parse_time(value: str, name: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must use HH:MM format") from exc


def is_submission_open(
    now_utc: datetime,
    start_time: time,
    end_time: time,
    timezone_name: str,
    always_open: bool = False,
) -> tuple[bool, datetime]:
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    local_now = now_utc.astimezone(ZoneInfo(timezone_name))
    inside_timebox = start_time <= local_now.time().replace(tzinfo=None) < end_time
    return always_open or (local_now.weekday() == 1 and inside_timebox), local_now


def validate_table_name(table_name: str) -> None:
    parts = table_name.split(".")
    if len(parts) != 3 or any(not IDENTIFIER_PART.fullmatch(part) for part in parts):
        raise ValueError("TARGET_TABLE must be a three-part catalog.schema.table identifier")


def build_overwrite_statement(
    table_name: str,
    market_choices: dict[str, bool],
    user_id: str,
    generated_at: datetime,
) -> str:
    validate_table_name(table_name)
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    if not market_choices:
        raise ValueError("At least one market must be configured")

    timestamp = generated_at.astimezone(timezone.utc)
    timestamp_literal = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    user_literal = _sql_string(user_id)
    rows = []
    for market, use_forecast in market_choices.items():
        normalized_market = market.strip().upper()
        if not MARKET_CODE.fullmatch(normalized_market):
            raise ValueError(f"Invalid market code: {market!r}")
        rows.append(
            f"('{normalized_market}', {str(bool(use_forecast)).upper()}, "
            f"{user_literal}, TIMESTAMP '{timestamp_literal}')"
        )

    values = ",\n    ".join(rows)
    return (
        f"INSERT OVERWRITE TABLE {table_name} "
        "SELECT Market, UseCurrentWeekFcst, UserID, GenerationTimestamp "
        f"FROM VALUES {values} "
        "AS submitted(Market, UseCurrentWeekFcst, UserID, GenerationTimestamp)"
    )


def _sql_string(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("User identity is empty or invalid")
    return "'" + value.replace("'", "''") + "'"