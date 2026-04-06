-- ===============================
-- ACTIVE ALARMS
-- ===============================
CREATE TABLE IF NOT EXISTS active_alarms (
    alarm_id TEXT PRIMARY KEY,
    alarm JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_updated TIMESTAMPTZ DEFAULT now()
);

-- ===============================
-- ALARM HISTORY
-- ===============================
CREATE TABLE IF NOT EXISTS alarm_history (
    alarm_id TEXT NOT NULL,
    alarm JSONB NOT NULL,
    cleared_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (alarm_id, cleared_at)
);

-- ===============================
-- TRIGGER FUNCTION
-- ===============================
CREATE OR REPLACE FUNCTION set_last_updated()
RETURNS trigger AS $$
BEGIN
  NEW.last_updated = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_active_alarms_updated ON active_alarms;

CREATE TRIGGER trg_active_alarms_updated
BEFORE UPDATE ON active_alarms
FOR EACH ROW
EXECUTE FUNCTION set_last_updated();

-- ===============================
-- INDEXES
-- ===============================
CREATE INDEX IF NOT EXISTS idx_active_alarms_alarm_gin
ON active_alarms USING GIN (alarm);

CREATE INDEX IF NOT EXISTS idx_alarm_history_alarm_gin
ON alarm_history USING GIN (alarm);