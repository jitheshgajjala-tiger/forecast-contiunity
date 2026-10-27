import os
from datetime import datetime, timezone

import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

from workflow import (
    DEFAULT_MARKETS,
    build_audit_select_statement,
    build_overwrite_statement,
    get_local_schedule,
    is_submission_open,
    validate_table_name,
)


st.set_page_config(page_title="Forecast continuity inputs", page_icon=":material/tune:", layout="centered")
st.title("Forecast continuity inputs")
st.caption("Select the markets that should use the current-week forecast, then submit the full snapshot.")

markets = [
    item.strip().upper()
    for item in os.getenv("MARKETS", ",".join(DEFAULT_MARKETS)).split(",")
    if item.strip()
]
if not markets:
    st.error("No markets are configured. Set MARKETS in the app environment.")
    st.stop()

try:
    always_open = os.getenv("ALWAYS_OPEN_FOR_TESTING", "false").strip().lower() == "true"
    start_time, end_time, timezone_name = get_local_schedule()
    open_now, local_now = is_submission_open(
        datetime.now(timezone.utc), start_time, end_time, timezone_name, always_open
    )
except ValueError as exc:
    st.error(f"Invalid schedule configuration: {exc}")
    st.stop()

if always_open:
    st.warning("Testing mode is enabled. Submissions are open at all times.")
elif open_now:
    st.success(f"Submission window is open until {end_time.strftime('%H:%M')} {timezone_name}.")
else:
    st.warning(
        f"Submission window is closed. It opens Tuesday at {start_time.strftime('%H:%M')} "
        f"{timezone_name}. Current local time: {local_now:%A %H:%M}."
    )

with st.form("market_selection"):
    columns = st.columns(3)
    for index, market in enumerate(markets):
        with columns[index % len(columns)]:
            st.checkbox(
                market,
                value=True,
                key=f"market_{market}",
                disabled=not open_now,
                help="Checked means use the current-week forecast for this market.",
            )

    submitted = st.form_submit_button("Submit", type="primary", disabled=not open_now)

if submitted:
    # Re-check after the form event so a late request cannot cross the deadline.
    open_at_submit, _ = is_submission_open(
        datetime.now(timezone.utc), start_time, end_time, timezone_name, always_open
    )
    if not open_at_submit:
        st.error("The submission window has closed. No changes were written.")
        st.stop()

    headers = st.context.headers
    user_id = (
        headers.get("x-forwarded-email")
        or headers.get("x-forwarded-user")
        or os.getenv("LOCAL_USER_ID")
    )
    if not user_id:
        st.error("Unable to identify the signed-in user. No changes were written.")
        st.stop()

    target_table = os.getenv("TARGET_TABLE", "")
    try:
        validate_table_name(target_table)
        selected_markets = {
            market: bool(st.session_state[f"market_{market}"]) for market in markets
        }
        statement = build_overwrite_statement(
            target_table,
            selected_markets,
            user_id,
            datetime.now(timezone.utc),
        )
        config = Config()
        warehouse_id = os.environ["WAREHOUSE_ID"]
        connection = sql.connect(
            server_hostname=config.host.removeprefix("https://"),
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
            credentials_provider=lambda: config.authenticate,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET TIME ZONE 'UTC'")
                cursor.execute(statement)
        finally:
            connection.close()
    except (KeyError, ValueError) as exc:
        st.error(f"Submission configuration error: {exc}. No changes were written.")
        st.stop()
    except Exception as exc:
        st.error(f"Submission failed. The previous table contents were not intentionally changed. Details: {exc}")
        st.stop()

    st.session_state["last_submitted_markets"] = selected_markets
    st.success("Submission saved. The backing table now contains this complete snapshot.")

last_submitted = st.session_state.get("last_submitted_markets")
if last_submitted:
    selected_count = sum(last_submitted.values())
    st.caption(f"Last successful submission in this browser session: {selected_count} of {len(markets)} markets enabled.")

st.subheader("Saved snapshot")
st.caption("Latest complete submission stored in the backing table. Checked markets have UseCurrentWeekFcst = true.")
st.button("Refresh saved snapshot", icon=":material/refresh:")

try:
    target_table = os.getenv("TARGET_TABLE", "")
    audit_statement = build_audit_select_statement(target_table)
    config = Config()
    warehouse_id = os.environ["WAREHOUSE_ID"]
    connection = sql.connect(
        server_hostname=config.host.removeprefix("https://"),
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: config.authenticate,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.execute(audit_statement)
            audit_columns = [column[0] for column in cursor.description]
            audit_rows = [dict(zip(audit_columns, row)) for row in cursor.fetchall()]
    finally:
        connection.close()

    if audit_rows:
        st.dataframe(audit_rows, hide_index=True, use_container_width=True)
    else:
        st.info("No submission has been saved yet.")
except Exception as exc:
    st.error(f"Unable to read the saved snapshot. Check the app's table read permissions. Details: {exc}")