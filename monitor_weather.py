#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timezone
import pytz
import requests

# Zona waktu default untuk cap waktu laporan
WIB = pytz.timezone("Asia/Jakarta")

# ✅ Ganti/ tambah kota di sini (lat, lon, timezone lokal)
CITIES = [
    {"name": "Jakarta, ID", "lat": -6.2,  "lon": 106.816, "tz": "Asia/Jakarta"},
    {"name": "Tokyo, JP",   "lat": 35.68, "lon": 139.69,  "tz": "Asia/Tokyo"},
    {"name": "London, UK",  "lat": 51.50, "lon": -0.12,   "tz": "Europe/London"},
    {"name": "Sydney, AU",  "lat": -33.86,"lon": 151.21,  "tz": "Australia/Sydney"},
    {"name": "San Francisco, US", "lat": 37.77, "lon": -122.42, "tz": "America/Los_Angeles"},
]

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

def wmo_code_to_text(code: int):
    mapping = {
        0:"Cerah", 1:"Cerah berawan", 2:"Berawan sebagian", 3:"Berawan",
        45:"Kabut", 48:"Kabut rime", 51:"Gerimis ringan", 53:"Gerimis sedang",
        55:"Gerimis lebat", 61:"Hujan ringan", 63:"Hujan sedang", 65:"Hujan lebat",
        66:"Hujan beku ringan", 67:"Hujan beku lebat", 71:"Salju ringan", 73:"Salju",
        75:"Salju lebat", 80:"Hujan rintik", 81:"Hujan deras", 82:"Hujan sangat deras",
        95:"Badai guntur", 96:"Badai guntur (es kecil)", 99:"Badai guntur (es besar)"
    }
    return mapping.get(code, f"Kode {code}")

def fetch_weather(lat, lon, tz):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,weather_code",
        "hourly": "precipitation,precipitation_probability",
        "forecast_hours": 2,
        "timezone": tz
    }
    r = requests.get(OPEN_METEO, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def section(title: str) -> str:
    return f"{title}\n{'=' * len(title)}"

def main():
    now_wib = datetime.now(timezone.utc).astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
    print(section(f"LAPORAN MONITORING CUACA (dibuat {now_wib})"))

    os.makedirs("reports", exist_ok=True)
    lines = []

    for city in CITIES:
        name, lat, lon, tz = city["name"], city["lat"], city["lon"], city["tz"]
        print(section(name))
        try:
            data = fetch_weather(lat, lon, tz)
        except Exception as e:
            msg = f"[{name}] ERROR: {e}"
            print(msg)
            lines.append(msg)
            continue

        cur = data.get("current") or {}
        if not cur:
            msg = f"[{name}] Tidak ada data current."
            print(msg)
            lines.append(msg)
            continue

        tlocal = cur.get("time")
        temp = cur.get("temperature_2m")
        rh = cur.get("relative_humidity_2m")
        wind = cur.get("wind_speed_10m")
        wind_dir = cur.get("wind_direction_10m")
        precip = cur.get("precipitation")
        wcode = int(cur.get("weather_code")) if cur.get("weather_code") is not None else -1
        cond = wmo_code_to_text(wcode)

        print(f"Waktu lokal : {tlocal}")
        print(f"Kondisi     : {cond}")
        print(f"Suhu        : {temp} °C | RH {rh}%")
        print(f"Angin       : {wind} m/s | Arah {wind_dir}°")
        print(f"Presipitasi : {precip} mm (sekarang)")

        hourly = data.get("hourly") or {}
        h_times = hourly.get("time") or []
        h_pp = hourly.get("precipitation_probability") or []
        h_pr = hourly.get("precipitation") or []
        if h_times and h_pp:
            print("Perkiraan 1–2 jam ke depan:")
            for i in range(min(2, len(h_times))):
                print(f"  • {h_times[i]} → Peluang hujan {h_pp[i]}%, Curah {h_pr[i]} mm")

        summary = f"[{name}] {tlocal} | {cond} | {temp}°C | RH {rh}% | Angin {wind}m/s ({wind_dir}°) | Hujan {precip}mm"
        lines.append(summary)

    with open("reports/weather_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\nLaporan ringkas tersimpan: reports/weather_report.txt")

if __name__ == "__main__":
    main()
