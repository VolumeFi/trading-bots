import json
import logging
import threading
import time
from contextlib import contextmanager

from psycopg.types.json import Jsonb
from psycopg_pool.pool import ConnectionPool

DB_POOL: ConnectionPool = None
REFRESH = threading.local()
CONN = threading.local()

WARM_DEXES = ("pancakeswap_new", "uniswap_v2", "uniswap_v3")


@contextmanager
def connect():
    with DB_POOL.connection() as conn:
        CONN.commit = conn.commit
        CONN.cursor = conn.cursor
        CONN.execute = conn.execute
        try:
            yield
        finally:
            delattr(CONN, "commit")
            delattr(CONN, "cursor")
            delattr(CONN, "execute")


def init():
    global DB_POOL
    DB_POOL = ConnectionPool("dbname=momentum_cache user=postgres")
    with DB_POOL.connection() as conn:
        conn.execute(
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
        conn.execute(
            """\
CREATE TABLE IF NOT EXISTS required_pairs (
dex TEXT,
from_coin TEXT NOT NULL,
to_coin TEXT NOT NULL,
PRIMARY KEY (dex, from_coin, to_coin)
)"""
        )
        conn.execute(
            """\
CREATE TABLE IF NOT EXISTS get_high_returns_warming_params (
params JSONB PRIMARY KEY,
ts TIMESTAMP WITHOUT TIME ZONE NOT NULL
)"""
        )
        for dex in WARM_DEXES:
            conn.execute(
                """\
INSERT INTO get_high_returns_warming_params
VALUES (%s, now() - interval '30 minutes')
ON CONFLICT DO NOTHING""",
                (
                    Jsonb(
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


def try_cache(path, params, f):
    with CONN.cursor() as cur:
        cur.execute(
            """\
SELECT value
FROM gecko
WHERE path = %s
AND params = %s
AND (
  now() - interval '5 minutes' <= ts -- Ignore use_cache if this entry is very young.
  OR (%s AND now() - max_age <= ts)
)
""",
            (path, Jsonb(params), getattr(REFRESH, "use_cache", True)),
        )
        value = cur.fetchone()
        if value is not None:
            return value[0]
        value = f()
        cur.execute(
            """\
INSERT INTO gecko(path, params, ts, max_age, value)
VALUES (%s, %s, now(), interval '3 hours', %s)
ON CONFLICT (path, params) DO UPDATE 
SET
     ts = EXCLUDED.ts,
max_age = EXCLUDED.max_age,
  value = EXCLUDED.value
""",
            (path, Jsonb(params), Jsonb(value)),
        )
        CONN.commit()
        return value


def get_pairs(dex):
    with CONN.cursor() as cur:
        cur.execute(
            """\
SELECT from_coin, to_coin FROM required_pairs
 WHERE dex = %s
""",
            (dex,),
        )
        return cur.fetchall()


def warm_cache_loop():
    import momentum_scanner_intraday

    REFRESH.use_cache = False
    while True:
        try:
            with DB_POOL.connection() as conn:
                # GC old data.
                conn.execute("""DELETE FROM gecko where ts < now() - max_age""")
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT params FROM get_high_returns_warming_params WHERE ts < now() - interval '30 minutes'"""
                    )
                    out_of_date = cur.fetchall()
            if out_of_date is not None:
                with connect():
                    for kwargs in out_of_date:
                        kwargs = kwargs[0]
                        logging.info(
                            "Running warming query with parameters %s",
                            json.dumps(kwargs),
                        )
                        momentum_scanner_intraday.get_high_returns(**kwargs)
                        CONN.execute(
                            """\
INSERT INTO get_high_returns_warming_params
VALUES (%s, now())
ON CONFLICT (params)
DO UPDATE SET ts = EXCLUDED.ts
""",
                            (Jsonb(kwargs),),
                        )
            else:
                logging.info("Cache is warm")
        except Exception:
            logging.exception("Error while attempting cache warming query")
        time.sleep(60)
