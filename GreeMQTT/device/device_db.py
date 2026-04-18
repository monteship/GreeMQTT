import sqlite3
from pathlib import Path
from typing import List, Optional

from GreeMQTT.device.device import Device
from GreeMQTT.logger import log


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


DB_PATH = str(get_project_root().parent / "devices.db")


class DeviceDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    device_ip TEXT NOT NULL,
                    is_GCM INTEGER NOT NULL,
                    `key` TEXT NOT NULL,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.execute("PRAGMA journal_mode=WAL")
            conn.close()
        except sqlite3.Error as e:
            log.error("Failed to initialize database", db_path=self.db_path, error=str(e))
            raise

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def __exit__(self, exc_type, exc_value, traceback):
        if hasattr(self, "conn"):
            self.conn.close()

    def get_device(self, device_id: str) -> Optional[Device]:
        with self as conn:
            c = conn.cursor()
            c.execute(
                "SELECT device_id, device_ip, `key`, is_GCM FROM devices WHERE device_id = ?",
                (device_id,),
            )
            row = c.fetchone()
            return (
                Device(
                    device_ip=row[1],
                    device_id=row[0],
                    name="Load from DB",
                    is_GCM=bool(row[3]),
                    key=row[2],
                )
                if row
                else None
            )

    def get_all_devices(self) -> List[Device]:
        with self as conn:
            c = conn.cursor()
            c.execute("SELECT device_id, device_ip, `key`, is_GCM FROM devices")
            rows = c.fetchall()
            return [
                Device(
                    device_ip=row[1],
                    device_id=row[0],
                    name="Load from DB",
                    is_GCM=bool(row[3]),
                    key=row[2],
                )
                for row in rows
            ]

    def save_device(self, device_id: str, device_ip: str, key: str, is_GCM: bool = False):
        with self as conn:
            c = conn.cursor()
            c.execute(
                "REPLACE INTO devices (device_id, device_ip, `key`, is_GCM) VALUES (?, ?, ?, ?)",
                (device_id, device_ip, key, int(is_GCM)),
            )
            conn.commit()

    def get_seen_at_devices(self) -> List:
        with self as conn:
            c = conn.cursor()
            c.execute("SELECT  device_ip, seen_at FROM devices ORDER BY seen_at DESC")
            rows = c.fetchall()
            return rows

    def update_seen_at(self, device_id: str):
        if not device_id:
            raise ValueError("device_id must not be empty")
        try:
            with self as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE devices SET seen_at = CURRENT_TIMESTAMP WHERE device_id = ?",
                    (device_id,),
                )
                conn.commit()
        except sqlite3.Error as e:
            log.error("Failed to update seen_at", device_id=device_id, error=str(e))
