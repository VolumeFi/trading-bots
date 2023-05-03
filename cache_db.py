import psycopg2

DB = None


def get_db():
    global DB
    if DB is None:
        DB = psycopg2.connect(dbname="momentum_cache")
        with DB.cursor() as db:
            db.execute(
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
    return DB.cursor()


def fetch(dex, lag_return, daily_volume, f):
    with get_db() as db:
        value = db.execute(
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
        if value is not None:
            return value
        value = f()
        print(value)
        db.execute(
            """\
INSERT INTO daily_high_returns(dex, lag_return, daily_volume, ts, value)
VALUES (%s, %s, %s, now(), %s)
ON CONFLICT (dex, lag_return, daily_volume) DO UPDATE 
SET ts = EXCLUDED.ts,
  value = EXCLUDED.value
""",
            (dex, lag_return, daily_volume, value),
        )
        row = db.execute(
            """\
SELECT *
FROM daily_high_returns
""",
            (dex, lag_return, daily_volume),
        )
        print(row)
        return value
