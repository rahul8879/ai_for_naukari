import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "retail.db"
REGIONS = ["West", "North", "South", "East"]
PRODUCTS = ["Electronics", "Home", "Grocery"]
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def query_rows(sql:str,params: tuple):
    with connect() as c:
        return [dict(row) for row in c.execute(sql, params).fetchall()]

