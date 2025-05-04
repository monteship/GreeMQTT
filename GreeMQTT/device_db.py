import sqlite3
import os
from typing import Optional, List

from GreeMQTT.device import Device

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
                device_id TEXT PRIMARY KEY,
                device_ip TEXT NOT NULL,
                is_gcm INTEGER NOT NULL,
                `key` TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get_device(self, mac: str) -> Optional[Device]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT mac, device_ip, `key`, is_gcm FROM devices WHERE mac = ?", (mac,)
        )
        row = c.fetchone()
        conn.close()
        return (
            Device(
                device_id=row[0],
                device_ip=row[1],
                key=row[2],
                is_GCM=bool(row[3]),
                name="Load from DB",
            )
            if row
            else None
        )

    def get_all_devices(self) -> List[Device]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT device_id, device_ip, `key`, is_gcm FROM devices")
        rows = c.fetchall()
        conn.close()
        return [
            Device(
                device_id=row[0],
                device_ip=row[1],
                key=row[2],
                is_GCM=bool(row[3]),
                name="Load from DB",
            )
            for row in rows
        ]

    def save_device(self, mac: str, ip: str, key: str, is_gcm: bool = False):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "REPLACE INTO devices (device_id, device_ip, `key`, is_gcm) VALUES (?, ?, ?, ?)",
            (mac, ip, key, int(is_gcm)),
        )
        conn.commit()
        conn.close()


device_db = DeviceDB()
device_db.init_db()
