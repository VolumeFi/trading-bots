from contextlib import contextmanager

import psycopg2
import psycopg2.pool
from psycopg2.extras import Json

DB_POOL = None


def get_pool():
    global DB_POOL
    if DB_POOL is None:
        DB_POOL = psycopg2.pool.SimpleConnectionPool(
            1, 20, user="postgres", dbname="momentum_cache"
        )
        conn = DB_POOL.getconn()
        with conn.cursor() as cur:
            cur.execute(
                """
CREATE TABLE IF NOT EXISTS gecko (
    path TEXT,
    params JSONB,
    ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    max_age INTERVAL NOT NULL,
    value JSONB NOT NULL,
    PRIMARY KEY (path, params)
)"""
            )
            conn.commit()
        DB_POOL.putconn(conn)
    return DB_POOL


@contextmanager
def get_db():
    conn = get_pool().getconn()
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
AND now() - max_age <= ts
""",
            (path, Json(params)),
        )
        value = db.fetchone()
        if value is not None:
            return value[0]
        value = f()
        db.execute(
            """\
INSERT INTO gecko(path, params, ts, max_age, value)
VALUES (%s, %s, now(), interval '10 minutes', %s)
ON CONFLICT (path, params) DO UPDATE 
SET
     ts = EXCLUDED.ts,
max_age = EXCLUDED.max_age,
  value = EXCLUDED.value
""",
            (path, Json(params), Json(value)),
        )
        return value
