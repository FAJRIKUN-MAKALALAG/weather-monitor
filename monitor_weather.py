#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import pytz
import requests

WIB = pytz.timezone("Asia/Jakarta")

# ========= KONFIGURASI LOKASI (ADM4) =========
# Ganti/isi sesuai kebutuhanmu. Format:
# {"name": "Nama Tampilan", "adm4": "kode_kelurahan_desa"}
BMKG_LOCS: List[Dict[str, str]] = [
    {"name": "Kemayoran, Jakarta Pusat",     "adm4": "31.71.03.1001"},
    {"name": "Airmadidi, Sulut",     "adm4": "71.71.06.1008"},
    # Tambahkan lokasi lain di sini
]
# ============================================

BMKG_ENDPOINT = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
TIMEOUT = (5, 30)           # (connect, read) detik
PAUSE_BETWEEN_CALLS = 0.5   # jeda antar lokasi

def section(title: str) -> str:
    return f"{title}\n{'=' * len(title)}"

def parse_dt_local(s: str) -> Optional[datetime]:
    # format: "YYYY-MM-DD HH:mm:ss"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def pick_nearest_slot(buckets: List[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """
    BMKG JSON: data[0]["cuaca"] = list harian; tiap hari = list slot 3-jam.
    Kita pilih slot terdekat yang waktunya >= sekarang (lokal lokasi).
    Kalau tidak ada, ambil slot terakhir yang tersedia.
    """
    # Flatten
    seq: List[Dict[str, Any]] = []
    for day in buckets:
        if isinstance(day, list):
            seq.extend(day)

    now_local = datetime.now().replace(microsecond=0)
    best = None
    best_dt = None

    for item in seq:
        ldt = parse_dt_local(item.get("local_datetime", ""))
        if not ldt:
            continue
        if ldt >= now_local:
            if best is None or ldt < best_dt:
                best = item
                best_dt = ldt

    if best is not None:
        return best

    # fallback: pakai slot terakhir valid
    for item in reversed(seq):
        ldt = parse_dt_local(item.get("local_datetime", ""))
        if ldt:
            return item
    return None

def fetch_bmkg_by_adm4(adm4: str) -> Dict[str, Any]:
    r = requests.get(BMKG_ENDPOINT, params={"adm4": adm4}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def main():
    now_wib = datetime.now(timezone.utc).astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
    print(section(f"LAPORAN MONITORING CUACA (BMKG) dibuat {now_wib}"))
    os.makedirs("reports", exist_ok=True)
    lines: List[str] = []

    for loc in BMKG_LOCS:
        name = loc["name"]
        adm4 = loc["adm4"]
        print(section(name))
        try:
            data = fetch_bmkg_by_adm4(adm4)
        except Exception as e:
            msg = f"[{name}] ERROR: {e}"
            print(msg)
            lines.append(msg)
            time.sleep(PAUSE_BETWEEN_CALLS)
            continue

        lokasi = data.get("lokasi", {})
        tzname = lokasi.get("timezone", "Asia/Jakarta")
        try:
            tz = pytz.timezone(tzname)
        except Exception:
            tz = WIB

        cuaca_harian = (data.get("data") or [{}])[0].get("cuaca") if (data.get("data")) else None
        if not cuaca_harian:
            msg = f"[{name}] Data 'cuaca' kosong/tidak ditemukan."
            print(msg)
            lines.append(msg)
            time.sleep(PAUSE_BETWEEN_CALLS)
            continue

        slot = pick_nearest_slot(cuaca_harian)
        if not slot:
            msg = f"[{name}] Tidak ada slot waktu yang valid."
            print(msg)
            lines.append(msg)
            time.sleep(PAUSE_BETWEEN_CALLS)
            continue

        tlocal = slot.get("local_datetime", "-")
        cond   = slot.get("weather_desc", "-")
        temp   = slot.get("t", "-")       # °C
        rh     = slot.get("hu", "-")      # %
        ws     = slot.get("ws", "-")      # km/j
        wd     = slot.get("wd", "-")      # arah angin dari (teks)
        tcc    = slot.get("tcc", "-")     # tutupan awan %
        vs     = slot.get("vs_text", "-") # jarak pandang (km, teks)

        print(f"Waktu lokal   : {tlocal} ({tz.zone})")
        print(f"Kondisi       : {cond}")
        print(f"Suhu / RH     : {temp} °C | {rh}%")
        print(f"Angin         : {ws} km/j dari {wd}")
        print(f"Tutupan awan  : {tcc}%")
        print(f"Jarak pandang : {vs}")

        summary = f"[{name}] {tlocal} | {cond} | {temp}°C | RH {rh}% | Angin {ws} km/j dari {wd} | Awan {tcc}% | Vis {vs}"
        lines.append(summary)

        time.sleep(PAUSE_BETWEEN_CALLS)

    # tulis ringkas untuk Jenkins artifact & notifikasi
    with open("reports/weather_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\nLaporan ringkas tersimpan: reports/weather_report.txt")

if __name__ == "__main__":
    main()
