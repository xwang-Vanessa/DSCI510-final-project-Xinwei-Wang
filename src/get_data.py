import os
import json
import time
import argparse
from datetime import datetime
import requests


def make_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


def nice_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d")


def safe_number(x):
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def flatten_one_obs(item):
    props = item.get("properties", {})
    out = {}
    out["time"] = props.get("timestamp")
    out["date"] = nice_date(props.get("timestamp", "")) if props.get("timestamp") else None

    out["temp_c"] = safe_number((props.get("temperature") or {}).get("value"))
    out["dewpoint_c"] = safe_number((props.get("dewpoint") or {}).get("value"))
    out["wind_dir_deg"] = safe_number((props.get("windDirection") or {}).get("value"))
    out["wind_speed_mps"] = safe_number((props.get("windSpeed") or {}).get("value"))
    out["wind_gust_mps"] = safe_number((props.get("windGust") or {}).get("value"))
    out["humidity_pct"] = safe_number((props.get("relativeHumidity") or {}).get("value"))
    out["pressure_pa"] = safe_number((props.get("barometricPressure") or {}).get("value"))
    out["precip_last_hr_mm"] = safe_number((props.get("precipitationLastHour") or {}).get("value"))

    out["station"] = props.get("station")
    out["raw_id"] = props.get("id")

    return out


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def save_csv(path, rows):
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return

    keys = list(rows[0].keys())
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            parts = []
            for k in keys:
                val = r.get(k)
                if val is None:
                    parts.append("")
                else:
                    s = str(val).replace('"', '""')
                    if "," in s or "\n" in s:
                        s = f'"{s}"'
                    parts.append(s)
            f.write(",".join(parts) + "\n")


def fetch_noaa_observations(station_id, start_iso, end_iso, user_agent):
    url = f"https://api.weather.gov/stations/{station_id}/observations"
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}

    all_items = []
    next_url = url
    params = {"start": start_iso, "end": end_iso, "limit": 100}

    while True:
        resp = requests.get(next_url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"weather.gov returned {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        items = data.get("features", [])
        all_items.extend(items)

        links = (data.get("properties") or {}).get("next")
        if not links:
            break

        next_url = links
        params = None
        time.sleep(0.3)

    return all_items


def run_one_range(station_id, start_iso, end_iso, out_folder, user_agent):
    raw_name = f"noaa_{station_id}_{start_iso[:10]}_{end_iso[:10]}"
    raw_json_path = os.path.join(out_folder, raw_name + ".json")
    raw_csv_path = os.path.join(out_folder, raw_name + ".csv")

    items = fetch_noaa_observations(station_id, start_iso, end_iso, user_agent)
    save_json(raw_json_path, items)

    flat = [flatten_one_obs(x) for x in items]
    save_csv(raw_csv_path, flat)

    return raw_json_path, raw_csv_path, len(items)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", default="KCQT")
    parser.add_argument("--user_agent", default="DSCI510-FinalProject (xwang663@usc.edu)")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--start", default="2015-11-01T00:00:00+00:00")
    parser.add_argument("--end", default="2024-11-30T23:59:59+00:00")
    parser.add_argument("--extra_start", default="2024-11-01T00:00:00+00:00")
    parser.add_argument("--extra_end", default="2024-12-31T23:59:59+00:00")
    args = parser.parse_args()

    make_folder(args.out)

    a_json, a_csv, a_n = run_one_range(args.station, args.start, args.end, args.out, args.user_agent)
    b_json, b_csv, b_n = run_one_range(args.station, args.extra_start, args.extra_end, args.out, args.user_agent)

    print("Saved:")
    print(a_json)
    print(a_csv)
    print(f"records: {a_n}")
    print(b_json)
    print(b_csv)
    print(f"records: {b_n}")


if __name__ == "__main__":
    main()