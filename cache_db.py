"""
SQLite caching layer for Instagram discovery results.
Prevents redundant Bing searches and speeds up repeat queries.

Schema:
  searches(keyword, usernames_json, timestamp)
  profiles(username, profile_json, timestamp)
"""

import sqlite3
import json
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "data", "cache.db")
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                keyword     TEXT PRIMARY KEY,
                usernames   TEXT NOT NULL,
                timestamp   REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                username    TEXT PRIMARY KEY,
                profile     TEXT NOT NULL,
                timestamp   REAL NOT NULL
            )
        """)
        conn.commit()


# ── Search cache ──────────────────────────────────────────────────────────────

def get_cached_search(keyword: str):
    """Return cached username list for keyword, or None if stale/missing."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT usernames, timestamp FROM searches WHERE keyword = ?",
            (keyword.lower(),)
        ).fetchone()
    if row and (time.time() - row["timestamp"]) < CACHE_TTL_SECONDS:
        return json.loads(row["usernames"])
    return None


def cache_search(keyword: str, usernames: list):
    """Persist username list for keyword."""
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO searches (keyword, usernames, timestamp) VALUES (?, ?, ?)",
            (keyword.lower(), json.dumps(usernames), time.time())
        )
        conn.commit()


# ── Profile cache ─────────────────────────────────────────────────────────────

def get_cached_profile(username: str):
    """Return cached profile dict, or None if stale/missing."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT profile, timestamp FROM profiles WHERE username = ?",
            (username.lower(),)
        ).fetchone()
    if row and (time.time() - row["timestamp"]) < CACHE_TTL_SECONDS:
        return json.loads(row["profile"])
    return None


def cache_profile(username: str, profile: dict):
    """Persist extracted profile dict."""
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO profiles (username, profile, timestamp) VALUES (?, ?, ?)",
            (username.lower(), json.dumps(profile), time.time())
        )
        conn.commit()


# Auto-initialise on import
init_db()
