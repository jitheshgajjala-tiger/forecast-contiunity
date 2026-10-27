CREATE TABLE IF NOT EXISTS catalog.schema.business_signal_inputs (
  Market STRING NOT NULL,
  UseCurrentWeekFcst BOOLEAN NOT NULL,
  UserID STRING NOT NULL,
  GenerationTimestamp TIMESTAMP NOT NULL
)
USING DELTA;