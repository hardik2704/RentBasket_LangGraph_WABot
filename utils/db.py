"""
Database connection manager for RentBasket WhatsApp Bot.
Uses psycopg2 with a simple connection pool.
Gracefully falls back to None if DATABASE_URL is not set.
"""

import os
import sys
import atexit

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Connection pool (lazy-initialized)
_pool = None
_db_available = None  # None = not checked yet, True/False = result


def is_db_available() -> bool:
    """Check if database is configured and reachable."""
    global _db_available
    if _db_available is not None:
        return _db_available

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ℹ️  DATABASE_URL not set — using file-based logging (fallback)")
        _db_available = False
        return False

    try:
        _get_pool()
        _db_available = True
        print("✅ Database connected successfully")
        return True
    except Exception as e:
        print(f"⚠️  Database connection failed: {e} — using file-based logging (fallback)")
        _db_available = False
        return False


def _get_pool():
    """Get or create the connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    try:
        from psycopg2 import pool as pg_pool
    except ImportError:
        raise ImportError("psycopg2-binary is required. Run: pip install psycopg2-binary")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    _pool = pg_pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=database_url,
    )
    return _pool


def get_connection():
    """
    Get a database connection from the pool.
    Use with a context manager or call put_connection() when done.
    """
    pool = _get_pool()
    return pool.getconn()


def put_connection(conn):
    """Return a connection to the pool."""
    if _pool is not None:
        _pool.putconn(conn)


def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """
    Execute a query with automatic connection management.

    Args:
        query: SQL query string with %s placeholders
        params: Tuple of parameters
        fetch: If True, return fetched rows

    Returns:
        List of rows if fetch=True, else None
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                result = cur.fetchall()
            else:
                result = None
            conn.commit()
            return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        put_connection(conn)


def execute_query_one(query: str, params: tuple = None):
    """Execute a query and return a single row."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchone()
            conn.commit()
            return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        put_connection(conn)


def _cleanup():
    """Close all connections on exit."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


atexit.register(_cleanup)
