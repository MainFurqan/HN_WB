import duckdb
from contextlib import contextmanager
from .config import settings


@contextmanager
def conn(read_only: bool = True):
    """Default to read-only so ingestion scripts can write to the same DB
    file while the API is up. Pass read_only=False only for migrations."""
    con = duckdb.connect(str(settings.duckdb_path), read_only=read_only)
    try:
        yield con
    finally:
        con.close()


def query(sql: str, params: list | None = None):
    with conn() as c:
        return c.execute(sql, params or []).fetchall()


def query_df(sql: str, params: list | None = None):
    with conn() as c:
        return c.execute(sql, params or []).df()
