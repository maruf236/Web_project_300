from contextlib import contextmanager
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from .config import Config

_pool = None

def pool():
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(1, 10, Config.DATABASE_URL)
    return _pool

@contextmanager
def tx():
    """Transaction scope: commit on success, rollback on any error."""
    conn = pool().getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool().putconn(conn)

def fetch_one(sql, params=()):
    with tx() as cur:
        cur.execute(sql, params)
        return cur.fetchone()

def fetch_all(sql, params=()):
    with tx() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def execute(sql, params=()):
    with tx() as cur:
        cur.execute(sql, params)
        return cur.rowcount

def audit(cur, actor_id, action, record_type=None, record_id=None, reason=None):
    cur.execute(
        "INSERT INTO audit_log(actor_id,action,record_type,record_id,reason) VALUES(%s,%s,%s,%s,%s)",
        (actor_id, action, record_type, str(record_id) if record_id else None, reason))
