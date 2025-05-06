import sqlite3
import os
from typing import Optional, List

from GreeMQTT.device.device import Device


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DB_PATH = os.path.join(get_project_root(), "..", "devices.db")
DB_PATH = os.path.abspath(DB_PATH)


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
                is_GCM INTEGER NOT NULL,
                `key` TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get_device(self, device_id: str) -> Optional[Device]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT device_id, device_ip, `key`, is_GCM FROM devices WHERE device_id = ?",
            (device_id,),
        )
        row = c.fetchone()
        conn.close()
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
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT device_id, device_ip, `key`, is_GCM FROM devices")
        rows = c.fetchall()
        conn.close()
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

    def save_device(
        self,
        device_id: str,
        device_ip: str,
        key: str,
        is_GCM: bool = False,
    ):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "REPLACE INTO devices (device_id, device_ip, `key`, is_GCM) VALUES (?, ?, ?, ?)",
            (device_id, device_ip, key, int(is_GCM)),
        )
        conn.commit()
        conn.close()
