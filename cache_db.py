import json
import logging
import threading
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
from psycopg2.extras import Json

DB_POOL: psycopg2.pool.SimpleConnectionPool = None
REFRESH = threading.local()


def init():
    global DB_POOL
    DB_POOL = psycopg2.pool.SimpleConnectionPool(
        1, 20, user="postgres", dbname="momentum_cache"
    )
    with get_db() as db:
        db.execute(
            """\
CREATE TABLE IF NOT EXISTS gecko (
path TEXT,
params JSONB,
ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
max_age INTERVAL NOT NULL,
value JSONB NOT NULL,
PRIMARY KEY (path, params)
)"""
        )
        db.execute(
            """\
CREATE TABLE IF NOT EXISTS required_pairs (
dex TEXT,
from_coin TEXT NOT NULL,
to_coin TEXT NOT NULL,
PRIMARY KEY (dex, from_coin, to_coin)
)"""
        )
        db.execute(
            """\
CREATE TABLE IF NOT EXISTS get_high_returns_warming_params (
params JSONB PRIMARY KEY,
ts TIMESTAMP WITHOUT TIME ZONE NOT NULL
)"""
        )
        for dex in ["uniswap_v2", "uniswap_v3"]:
            db.execute(
                """\
INSERT INTO get_high_returns_warming_params
VALUES (%s, now() - interval '1 hour')
ON CONFLICT DO NOTHING""",
                (
                    Json(
                        {
                            "dex": dex,
                            "lag_return": 6,
                            "daily_volume": 0,
                            "vol_30": 0,
                            "market_cap": 0,
                        }
                    ),
                ),
            )


@contextmanager
def get_db():
    conn = DB_POOL.getconn()
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        DB_POOL.putconn(conn)


def try_cache(path, params, f):
    with get_db() as db:
        db.execute(
            """\
SELECT value
FROM gecko
WHERE path = %s
AND params = %s
AND (%s AND now() - max_age <= ts)
""",
            (path, Json(params), getattr(REFRESH, "use_cache", True)),
        )
        value = db.fetchone()
        if value is not None:
            return value[0]
        value = f()
        db.execute(
            """\
INSERT INTO gecko(path, params, ts, max_age, value)
VALUES (%s, %s, now(), interval '1 hour', %s)
ON CONFLICT (path, params) DO UPDATE 
SET
     ts = EXCLUDED.ts,
max_age = EXCLUDED.max_age,
  value = EXCLUDED.value
""",
            (path, Json(params), Json(value)),
        )
        return value


def get_pairs(dex):
    with get_db() as db:
        db.execute(
            """\
SELECT from_coin, to_coin FROM required_pairs
 WHERE dex = %s
"""
        )
        return list(db.fetchall())


def warm_cache_loop():
    import momentum_scanner_intraday

    REFRESH.use_cache = False
    while True:
        try:
            with get_db() as db:
                db.execute(
                    """SELECT params FROM get_high_returns_warming_params WHERE now() - interval '30 minutes' < ts"""
                )
                kwargs = db.fetchone()
                if kwargs is not None:
                    kwargs = kwargs[0]
                    logging.info(
                        "Running warming query with parameters %s", json.dumps(kwargs)
                    )
                    momentum_scanner_intraday.get_high_returns(**kwargs)
                    db.execute(
                        """INSERT INTO get_high_returns_warming_params VALUES (%s, now())""",
                        (Json(kwargs),),
                    )
                else:
                    logging.info("Cache is warm")
        except Exception:
            logging.exception("Error while attempting cache warming query")
        time.sleep(60)
