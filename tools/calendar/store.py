import json
import sqlite3
import time

from tools.calendar.config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                user_key TEXT PRIMARY KEY,
                token_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()


def save_token(token_data: dict, user_key: str = "default") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO oauth_tokens(user_key, token_json, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(user_key)
            DO UPDATE SET token_json=excluded.token_json, updated_at=excluded.updated_at
            """,
            (user_key, json.dumps(token_data), int(time.time())),
        )
        conn.commit()


def load_token(user_key: str = "default") -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT token_json FROM oauth_tokens WHERE user_key = ?", (user_key,)
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None


def delete_token(user_key: str = "default") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM oauth_tokens WHERE user_key = ?", (user_key,))
        conn.commit()


def set_sync_state(state_key: str, state_value: dict) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO sync_state(state_key, state_value, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(state_key)
            DO UPDATE SET state_value=excluded.state_value, updated_at=excluded.updated_at
            """,
            (state_key, json.dumps(state_value), int(time.time())),
        )
        conn.commit()


def get_sync_state(state_key: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT state_value FROM sync_state WHERE state_key = ?",
            (state_key,),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None


def save_oauth_state(state: str, ttl_seconds: int = 900) -> None:
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO oauth_states(state, expires_at, created_at)
            VALUES(?, ?, ?)
            ON CONFLICT(state)
            DO UPDATE SET expires_at=excluded.expires_at, created_at=excluded.created_at
            """,
            (state, now + ttl_seconds, now),
        )
        conn.commit()


def consume_oauth_state(state: str) -> bool:
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT expires_at FROM oauth_states WHERE state = ?", (state,)).fetchone()
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
    if not row:
        return False
    return int(row[0]) >= now


def cleanup_oauth_states() -> None:
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM oauth_states WHERE expires_at < ?", (now,))
        conn.commit()
