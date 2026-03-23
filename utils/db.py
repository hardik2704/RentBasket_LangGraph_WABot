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

_last_check_time = 0
RETRY_INTERVAL = 60 # Check again after 60 seconds if it failed

def is_db_available() -> bool:
    """Check if database is configured and reachable."""
    global _db_available, _last_check_time
    
    import time
    now = time.time()
    
    # If it's already marked as available, keep it
    if _db_available is True:
        return True
        
    # If never checked OR if it failed but 60s have passed, try again
    if _db_available is None or (now - _last_check_time > RETRY_INTERVAL):
        _last_check_time = now
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            if _db_available is None: # Only print once
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
            
    return _db_available


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
    
    # Ensure sslmode=require for Supabase
    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

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
    conn = pool.getconn()
    
    # Simple validation: if connection is closed or broken, try once to get a new one
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:
        print("⚠️  Detecting stale connection, refreshing...")
        try:
            pool.putconn(conn, close=True) # Force close
            conn = pool.getconn()
        except Exception:
            pass # Return the original (possibly broken) and let the query fail/retry
            
    return conn


def put_connection(conn, close=False):
    """Return a connection to the pool."""
    if _pool is not None:
        _pool.putconn(conn, close=close)


import time
from functools import wraps

def retry_db_query(max_retries=3, delay=1):
    """Decorator to retry DB queries on connection errors."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_err = None
            for i in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    # List of common transient/connection errors
                    err_str = str(e).lower()
                    is_transient = any(msg in err_str for msg in [
                        "connection refused",
                        "operation timed out",
                        "ssl syscall error",
                        "could not receive data from server",
                        "connection reset",
                        "terminating connection due to administrator command"
                    ])
                    
                    if not is_transient:
                        raise e # Re-raise if it's a syntax or logic error
                        
                    print(f"⚠️  DB query attempt {i+1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                    
                    # Force pool refresh if multiple failures
                    if i > 0 and _pool:
                        try:
                            _cleanup()
                            _get_pool()
                        except Exception:
                            pass
            raise last_err
        return wrapper
    return decorator


@retry_db_query(max_retries=3, delay=1)
def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """
    Execute a query with automatic connection management and retries.
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


@retry_db_query(max_retries=3, delay=1)
def execute_query_one(query: str, params: tuple = None):
    """Execute a query and return a single row with retries."""
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
        try:
            _pool.closeall()
        except Exception:
            pass
        _pool = None


atexit.register(_cleanup)
