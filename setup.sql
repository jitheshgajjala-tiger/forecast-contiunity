CREATE CATALOG IF NOT EXISTS forecast_continuity_demo;

CREATE SCHEMA IF NOT EXISTS forecast_continuity_demo.business_inputs;

CREATE TABLE IF NOT EXISTS forecast_continuity_demo.business_inputs.business_signal_inputs (
  Market STRING NOT NULL,
  UseCurrentWeekFcst BOOLEAN NOT NULL,
  UserID STRING NOT NULL,
  GenerationTimestamp TIMESTAMP NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS forecast_continuity_demo.business_inputs.business_signal_history (
  SubmissionID STRING NOT NULL,
  Market STRING NOT NULL,
  UseCurrentWeekFcst BOOLEAN NOT NULL,
  UserID STRING NOT NULL,
  GenerationTimestamp TIMESTAMP NOT NULL
)
USING DELTA;