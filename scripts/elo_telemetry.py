#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Terminal operating health and hardware telemetry store."""
from pathlib import Path
import sqlite3
import threading
import time


class TelemetryStore:
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.lock = threading.RLock()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self.lock:
            with sqlite3.connect(self.path) as con:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recorded_at REAL NOT NULL,
                        cpu_temp_c REAL,
                        voltage_v REAL,
                        cpu_load_1m REAL,
                        throttled INTEGER,
                        under_voltage INTEGER,
                        memory_free_mb REAL,
                        disk_free_mb REAL,
                        wifi_rssi_dbm REAL,
                        uptime_seconds REAL,
                        display_frames INTEGER
                    )
                """)
                con.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry (recorded_at)")

    def record(self, data, now=None):
        if not isinstance(data, dict):
            raise ValueError('Invalid telemetry payload')
        now = time.time() if now is None else now

        def _num(key, min_val, max_val):
            val = data.get(key)
            if val is None:
                return None
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f'Invalid {key}')
            if not min_val <= val <= max_val:
                raise ValueError(f'{key} out of range')
            return round(float(val), 2)

        cpu_temp = _num('cpu_temp_c', -40.0, 150.0)
        voltage = _num('voltage_v', 0.0, 24.0)
        cpu_load = _num('cpu_load_1m', 0.0, 256.0)
        throttled = data.get('throttled')
        if throttled is not None:
            if not isinstance(throttled, int) or isinstance(throttled, bool) or not 0 <= throttled <= 0xFFFFFFFF:
                raise ValueError('Invalid throttled flags')
        under_voltage = data.get('under_voltage')
        if under_voltage is not None:
            if not isinstance(under_voltage, bool):
                raise ValueError('Invalid under_voltage flag')
        elif throttled is not None:
            under_voltage = bool(throttled & 0x10001)

        mem_free = _num('memory_free_mb', 0.0, 1048576.0)
        disk_free = _num('disk_free_mb', 0.0, 10485760.0)
        rssi = _num('wifi_rssi_dbm', -120.0, 0.0)
        uptime = _num('uptime_seconds', 0.0, 315360000.0)
        frames = data.get('display_frames')
        if frames is not None and (not isinstance(frames, int) or isinstance(frames, bool) or frames < 0):
            frames = None

        with self.lock:
            with sqlite3.connect(self.path) as con:
                con.execute("""
                    INSERT INTO telemetry (recorded_at, cpu_temp_c, voltage_v, cpu_load_1m, throttled, under_voltage,
                                           memory_free_mb, disk_free_mb, wifi_rssi_dbm, uptime_seconds, display_frames)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (now, cpu_temp, voltage, cpu_load, throttled, int(bool(under_voltage)) if under_voltage is not None else None,
                      mem_free, disk_free, rssi, uptime, frames))
                con.execute("DELETE FROM telemetry WHERE id < (SELECT coalesce(max(id), 0) - 10000 FROM telemetry)")

    def latest(self):
        with self.lock:
            with sqlite3.connect(self.path) as con:
                cur = con.cursor()
                cur.execute("""
                    SELECT recorded_at, cpu_temp_c, voltage_v, cpu_load_1m, throttled, under_voltage,
                           memory_free_mb, disk_free_mb, wifi_rssi_dbm, uptime_seconds, display_frames
                    FROM telemetry ORDER BY id DESC LIMIT 1
                """)
                row = cur.fetchone()
                if not row:
                    return None
                under_voltage = bool(row[5]) if row[5] is not None else False
                temp = row[1]
                volts = row[2]
                load = row[3]
                rssi = row[8]
                alerts = []
                if under_voltage:
                    alerts.append('subtensao_detectada')
                if volts is not None and volts < 4.75:
                    alerts.append('tensao_baixa')
                if temp is not None and temp >= 80.0:
                    alerts.append('temperatura_critica')
                elif temp is not None and temp >= 72.0:
                    alerts.append('temperatura_elevada')
                if rssi is not None and rssi <= -80.0:
                    alerts.append('sinal_wifi_fraco')

                return {
                    'recorded_at': row[0],
                    'cpu_temp_c': temp,
                    'voltage_v': volts,
                    'cpu_load_1m': load,
                    'throttled': row[4],
                    'under_voltage': under_voltage,
                    'memory_free_mb': row[6],
                    'disk_free_mb': row[7],
                    'wifi_rssi_dbm': rssi,
                    'uptime_seconds': row[9],
                    'display_frames': row[10],
                    'alerts': alerts
                }
