# Forecast continuity inputs

Streamlit prototype for the business-input workflow in slides 22–24.

## Behavior

- Every new browser session defaults all configured markets to checked.
- The Tuesday submission window is enforced by the app using the configured business timezone.
- `ALWAYS_OPEN_FOR_TESTING=true` keeps submissions available at all times for demos; turn it off before production.
- Market choices live in a Streamlit form. No table write occurs until Submit is pressed.
- Submit overwrites the latest-snapshot Delta table and appends one row per configured market to the history table, sharing a submission ID and capturing the signed-in user plus a UTC generation timestamp.
- The read-only refresh control reloads the latest snapshot and full submission history from Databricks; it does not write data.
- The last successful submission is shown for the current browser session. Drafts are not written to the table.

The submission window and target table are intentionally unconfigured in `app.yaml`; the app remains closed until the process owners confirm the Tuesday window and the Databricks owner supplies the real three-part table name. The prototype does not send email or orchestrate app lifecycle yet.

## Databricks setup

1. Run `setup.sql` to create the latest-snapshot and append-only history Delta tables. For an existing deployment, run it again to add the history table.
2. Create a Databricks App and add the SQL warehouse as an app resource with `Can use` permission.
3. Grant the app service principal `USE CATALOG`, `USE SCHEMA`, and `MODIFY` on both tables, plus `SELECT` to show the latest snapshot and history. The app writes using its own identity; the signed-in user identity is recorded separately for business audit.
4. Deploy this folder from a Git repository or workspace folder. Configure `TARGET_TABLE`, `HISTORY_TABLE`, `WINDOW_START`, `WINDOW_END`, `BUSINESS_TIMEZONE`, and `MARKETS` in `app.yaml`.
5. Grant app `CAN USE` only to the approved Super User group.

Do not add personal access tokens to the app. Databricks Apps injects app credentials, and the SQL warehouse ID is supplied by the app resource.

## Lifecycle and notifications

Use a scheduled Databricks Workflow or an approved external scheduler to call the Databricks Apps Start API shortly before the opening time and Stop API at the close. Use a dedicated automation identity with permission to manage this app. The orchestration should send startup and shutdown emails, including the app URL in the startup notice. The app itself also rejects submissions outside the window, so a delayed stop cannot permit late writeback.

The exact APIs are `POST /api/2.0/apps/{name}/start` and `POST /api/2.0/apps/{name}/stop`. Configure the email action using the organization's approved email integration. A successful-submission CSV attachment can be added after the notification route is chosen.

## Local development

Install `requirements.txt`, then run:

```powershell
$env:LOCAL_USER_ID = "developer@example.com"
streamlit run app.py
```

The write path requires Databricks app credentials and a configured `WAREHOUSE_ID` and `TARGET_TABLE`; the submission window must also be set. For local development, set `DATABRICKS_HOST`, `WAREHOUSE_ID`, `TARGET_TABLE`, `WINDOW_START`, and `WINDOW_END`, then authenticate with the Databricks SDK's supported local profile. Do not use the local identity override in a deployed app.

Run the schedule and SQL-generation unit tests with:

```powershell
python -m unittest discover -s tests
```

## Prototype limitations to confirm

- The market list is configurable through `MARKETS`. If business owners need to add markets without a deployment, move this list to a separate governed market-configuration table and grant the app read access.
- Draft selections are session-local. If concurrent users must share a live draft, define a shared temporary-state store and locking behavior.
- Validate the Databricks SQL `INSERT OVERWRITE ... VALUES` statement against the target warehouse and table during the feasibility test.
- Add start/stop email delivery and optional CSV attachment after the distribution list and approved email service are known.