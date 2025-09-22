#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from datetime import datetime, timezone

import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================== Konfigurasi ==================
WIB = pytz.timezone("Asia/Jakarta")

# ✅ Ganti/ tambah kota di sini (lat, lon, timezone lokal)
CITIES = [
    {"name": "Jakarta, ID",          "lat": -6.2,   "lon": 106.816,  "tz": "Asia/Jakarta"},
    {"name": "Tokyo, JP",            "lat": 35.68,  "lon": 139.69,   "tz": "Asia/Tokyo"},
    {"name": "London, UK",           "lat": 51.50,  "lon": -0.12,    "tz": "Europe/London"},
    {"name": "Sydney, AU",           "lat": -33.86, "lon": 151.21,   "tz": "Australia/Sydney"},
    {"name": "San Francisco, US",    "lat": 37.77,  "lon": -122.42,  "tz": "America/Los_Angeles"},
]

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# Timeout (connect, read) dalam detik
TIMEOUT = (5, 60)   # connect 5s, read 60s
# Jeda antar kota (detik) untuk menghindari burst / rate-limit
PAUSE_BETWEEN_CITIES = 0.8
# =================================================


def wmo_code_to_text(code: int) -> str:
    mapping = {
        0: "Cerah", 1: "Cerah berawan", 2: "Berawan sebagian", 3: "Berawan",
        45: "Kabut", 48: "Kabut rime", 51: "Gerimis ringan", 53: "Gerimis sedang",
        55: "Gerimis lebat", 61: "Hujan ringan", 63: "Hujan sedang", 65: "Hujan lebat",
        66: "Hujan beku ringan", 67: "Hujan beku lebat", 71: "Salju ringan", 73: "Salju",
        75: "Salju lebat", 80: "Hujan rintik", 81: "Hujan deras", 82: "Hujan sangat deras",
        95: "Badai guntur", 96: "Badai guntur (es kecil)", 99: "Badai guntur (es besar)"
    }
    return mapping.get(code, f"Kode {code}")


def make_session() -> requests.Session:
    """
    Session dengan retry + exponential backoff.
    """
    retry = Retry(
        total=3,                 # total percobaan ulang
        connect=3,
        read=3,
        backoff_factor=1.5,      # 0s, 1.5s, 3s, 4.5s ...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False
    )
    s = requests.Session()
    s.headers.update({"User-Agent": "weather-monitor-jenkins/1.0"})
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    return s


def fetch_weather(session: requests.Session, lat: float, lon: float, tz: str, timeout=TIMEOUT) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,weather_code",
        "hourly": "precipitation,precipitation_probability",
        "forecast_hours": 2,
        "timezone": tz,
    }
    r = session.get(OPEN_METEO, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def section(title: str) -> str:
    return f"{title}\n{'=' * len(title)}"


def main():
    now_wib = datetime.now(timezone.utc).astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
    print(section(f"LAPORAN MONITORING CUACA (dibuat {now_wib})"))

    os.makedirs("reports", exist_ok=True)
    lines = []

    session = make_session()

    for idx, city in enumerate(CITIES):
        name, lat, lon, tz = city["name"], city["lat"], city["lon"], city["tz"]
        print(section(name))
        try:
            data = fetch_weather(session, lat, lon, tz)
        except Exception as e:
            msg = f"[{name}] ERROR: {e}"
            print(msg)
            lines.append(msg)
            # jeda kecil sebelum lanjut kota berikutnya
            time.sleep(PAUSE_BETWEEN_CITIES)
            continue

        cur = data.get("current") or {}
        if not cur:
            msg = f"[{name}] Tidak ada data current."
            print(msg)
            lines.append(msg)
            time.sleep(PAUSE_BETWEEN_CITIES)
            continue

        tlocal   = cur.get("time")
        temp     = cur.get("temperature_2m")
        rh       = cur.get("relative_humidity_2m")
        wind     = cur.get("wind_speed_10m")
        wind_dir = cur.get("wind_direction_10m")
        precip   = cur.get("precipitation")
        wcode    = int(cur.get("weather_code")) if cur.get("weather_code") is not None else -1
        cond     = wmo_code_to_text(wcode)

        print(f"Waktu lokal : {tlocal}")
        print(f"Kondisi     : {cond}")
        print(f"Suhu        : {temp} °C | RH {rh}%")
        print(f"Angin       : {wind} m/s | Arah {wind_dir}°")
        print(f"Presipitasi : {precip} mm (sekarang)")

        hourly  = data.get("hourly") or {}
        h_times = hourly.get("time") or []
        h_pp    = hourly.get("precipitation_probability") or []
        h_pr    = hourly.get("precipitation") or []
        if h_times and h_pp:
            print("Perkiraan 1–2 jam ke depan:")
            for i in range(min(2, len(h_times))):
                print(f"  • {h_times[i]} → Peluang hujan {h_pp[i]}%, Curah { (h_pr[i] if i < len(h_pr) else 0) } mm")

        summary = f"[{name}] {tlocal} | {cond} | {temp}°C | RH {rh}% | Angin {wind}m/s ({wind_dir}°) | Hujan {precip}mm"
        lines.append(summary)

        # jeda kecil antar kota
        time.sleep(PAUSE_BETWEEN_CITIES)

    # Tulis ringkasan ke file (dipakai Jenkins untuk artifact & notifikasi)
    with open("reports/weather_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\nLaporan ringkas tersimpan: reports/weather_report.txt")


if __name__ == "__main__":
    main()
