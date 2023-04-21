import sqlite3

DB = None


def get_db():
    global DB
    if DB is None:
        DB = sqlite3.connect("momentum_cache.db")
        DB.execute("PRAGMA journal_mode = wal")
        DB.execute(
            """
CREATE TABLE IF NOT EXISTS cache (
    id TEXT,
    timestamp TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY(id)
)"""
        )
    return DB


def id_str(args):
    return f"{args[0]}({','.join(map(str, args[1:]))})"


def fetch(id, f):
    id = id_str(id)
    db = get_db()
    row = db.execute(
        """\
SELECT value
  FROM cache
 WHERE id = ?
   AND datetime('now', '-1 minute')  <= timestamp
""",
        (id,),
    ).fetchone()
    if row is not None:
        return row[0]
    value = f()
    db.execute(
        """\
INSERT OR REPLACE INTO cache
VALUES (?, datetime('now'), ?)
""",
        (id, value),
    )
    db.commit()
    return value
