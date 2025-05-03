import sqlite3
from typing import Optional, Tuple
import os

DB_PATH = os.path.join(os.getcwd(), "devices.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            is_gcm INTEGER NOT NULL,
            `key` TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_device(mac: str) -> Optional[Tuple[str, str, str]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT mac, ip, `key`, is_gcm FROM devices WHERE mac = ?", (mac,))
    row = c.fetchone()
    conn.close()
    return row


def get_all_devices() -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT mac, ip, `key`, is_gcm FROM devices")
    rows = c.fetchall()
    conn.close()
    return rows


def save_device(mac: str, ip: str, key: str, is_gcm: bool = False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "REPLACE INTO devices (mac, ip, `key`, is_gcm) VALUES (?, ?, ?, ?)",
        (mac, ip, key, is_gcm),
    )
    conn.commit()
    conn.close()
