import psycopg2
from psycopg2.extras import Json

INITIALIZED = False


def get_db():
    global INITIALIZED
    conn = psycopg2.connect(user="postgres", dbname="momentum_cache")
    conn.autocommit = True
    if not INITIALIZED:
        INITIALIZED = True
        with conn.cursor() as cur:
            cur.execute(
                """
CREATE TABLE IF NOT EXISTS daily_high_returns (
    dex TEXT,
    lag_return INTEGER,
    daily_volume INTEGER,
    ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    value JSONB NOT NULL,
    PRIMARY KEY (dex, lag_return, daily_volume)
)"""
            )
        INITIALIZED = True
    return conn


def fetch(dex, lag_return, daily_volume, f):
    with get_db() as conn:
        with conn.cursor() as db:
            db.execute(
                """\
SELECT value
  FROM daily_high_returns
 WHERE dex = %s
   AND lag_return = %s
   AND daily_volume = %s
   AND now() - interval '3 hours' <= ts
""",
                (dex, lag_return, daily_volume),
            )
            value = db.fetchone()
            if value is not None:
                return value[0]
            value = f()
            db.execute(
                """\
INSERT INTO daily_high_returns(dex, lag_return, daily_volume, ts, value)
VALUES (%s, %s, %s, now(), %s)
ON CONFLICT (dex, lag_return, daily_volume) DO UPDATE 
SET ts = EXCLUDED.ts,
 value = EXCLUDED.value
""",
                (dex, lag_return, daily_volume, Json(value)),
            )
            conn.commit()
