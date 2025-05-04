import sqlite3
from typing import Optional, Tuple, List
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "devices.db")


class DeviceDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
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

    def get_device(self, mac: str) -> Optional[Tuple[str, str, str, int]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT mac, ip, `key`, is_gcm FROM devices WHERE mac = ?", (mac,))
        row = c.fetchone()
        conn.close()
        return row

    def get_all_devices(self) -> List[Tuple[str, str, str, int]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT mac, ip, `key`, is_gcm FROM devices")
        rows = c.fetchall()
        conn.close()
        return rows

    def save_device(self, mac: str, ip: str, key: str, is_gcm: bool = False):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "REPLACE INTO devices (mac, ip, `key`, is_gcm) VALUES (?, ?, ?, ?)",
            (mac, ip, key, int(is_gcm)),
        )
        conn.commit()
        conn.close()


device_db = DeviceDB()
device_db.init_db()
