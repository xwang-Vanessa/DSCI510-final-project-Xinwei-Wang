
import os
import time
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup


def make_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


def grab_html(url, headers):
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"timeanddate returned {r.status_code}: {r.text[:200]}")
    return r.text


def save_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def clean_text(s):
    if s is None:
        return ""
    return " ".join(s.replace("\xa0", " ").split())


def pick_first_table(soup):
    tables = soup.find_all("table")
    best = None
    best_cols = 0
    for t in tables:
        first_row = t.find("tr")
        if not first_row:
            continue
        cols = first_row.find_all(["th", "td"])
        if len(cols) > best_cols:
            best_cols = len(cols)
            best = t
    return best


def parse_hourly_rows(html_text, year, month):
    soup = BeautifulSoup(html_text, "html.parser")

    table = soup.find("table", id="wt-his")
    if table is None:
        table = soup.find("table", class_="zebra tb-wt fw va-m")
    if table is None:
        table = pick_first_table(soup)
    if table is None:
        return []

    rows = table.find_all("tr")

    data = []
    current_day = None

    for tr in rows:
        cells = tr.find_all("td")
        if not cells:
            continue

        first = clean_text(cells[0].get_text(" ", strip=True))
        if first.lower().startswith(("mon", "tue", "wed", "thu", "fri", "sat", "sun")):
            current_day = first
            continue

        if current_day is None:
            continue

        time_str = clean_text(cells[0].get_text(" ", strip=True))
        if ":" not in time_str:
            continue

        temp_str = clean_text(cells[1].get_text(" ", strip=True))
        weather_str = clean_text(cells[2].get_text(" ", strip=True)) if len(cells) > 2 else ""
        wind_str = clean_text(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else ""
        humidity_str = clean_text(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else ""
        pressure_str = clean_text(cells[5].get_text(" ", strip=True)) if len(cells) > 5 else ""
        vis_str = clean_text(cells[6].get_text(" ", strip=True)) if len(cells) > 6 else ""

        data.append(
            {
                "year": year,
                "month": month,
                "day_label": current_day,
                "time_label": time_str,
                "temp_text": temp_str,
                "weather_text": weather_str,
                "wind_text": wind_str,
                "humidity_text": humidity_str,
                "pressure_text": pressure_str,
                "visibility_text": vis_str,
            }
        )

    return data


def grab_number(s):
    if s is None:
        return None
    keep = []
    for ch in s:
        if ch.isdigit() or ch in ".-":
            keep.append(ch)
        elif keep:
            break
    try:
        return float("".join(keep))
    except Exception:
        return None


def day_num_from_label(day_label):
    if not day_label:
        return None
    parts = day_label.split()
    for p in parts:
        if p.isdigit():
            return int(p)
        if p.endswith(",") and p[:-1].isdigit():
            return int(p[:-1])
    return None


def to_date_text(year, month, day_num):
    try:
        return datetime(year, month, day_num).strftime("%Y-%m-%d")
    except Exception:
        return None


def summarize_daily(hourly_rows):
    bucket = {}

    for r in hourly_rows:
        d = day_num_from_label(r.get("day_label", ""))
        if d is None:
            continue

        key = (r["year"], r["month"], d)
        if key not in bucket:
            bucket[key] = {
                "temps": [],
                "humidities": [],
                "pressures": [],
                "vis": [],
            }

        t = grab_number(r.get("temp_text", ""))
        if t is not None:
            bucket[key]["temps"].append(t)

        h = grab_number(r.get("humidity_text", ""))
        if h is not None:
            bucket[key]["humidities"].append(h)

        p = grab_number(r.get("pressure_text", ""))
        if p is not None:
            bucket[key]["pressures"].append(p)

        v = grab_number(r.get("visibility_text", ""))
        if v is not None:
            bucket[key]["vis"].append(v)

    out = []
    for (y, m, d), stuff in sorted(bucket.items()):
        temps = stuff["temps"]
        hum = stuff["humidities"]
        pres = stuff["pressures"]
        vis = stuff["vis"]

        row = {}
        row["date"] = to_date_text(y, m, d)
        row["year"] = y
        row["month"] = m
        row["day"] = d

        row["temp_high_f"] = max(temps) if temps else None
        row["temp_low_f"] = min(temps) if temps else None
        row["temp_avg_f"] = (sum(temps) / len(temps)) if temps else None

        row["humidity_avg_pct"] = (sum(hum) / len(hum)) if hum else None
        row["pressure_avg"] = (sum(pres) / len(pres)) if pres else None
        row["visibility_avg"] = (sum(vis) / len(vis)) if vis else None

        out.append(row)

    return out


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


def run_one_month(city_slug, year, month, out_folder, headers, sleep_sec=0.6):
    url = f"https://www.timeanddate.com/weather/usa/{city_slug}/historic?month={month}&year={year}"
    html_text = grab_html(url, headers)

    raw_html_name = f"timeanddate_{city_slug}_{year}_{month:02d}.html"
    raw_html_path = os.path.join(out_folder, raw_html_name)
    save_text(raw_html_path, html_text)

    hourly = parse_hourly_rows(html_text, year, month)
    hourly_csv_name = f"timeanddate_{city_slug}_{year}_{month:02d}_hourly.csv"
    hourly_csv_path = os.path.join(out_folder, hourly_csv_name)
    save_csv(hourly_csv_path, hourly)

    daily = summarize_daily(hourly)
    daily_csv_name = f"timeanddate_{city_slug}_{year}_{month:02d}_daily.csv"
    daily_csv_path = os.path.join(out_folder, daily_csv_name)
    save_csv(daily_csv_path, daily)

    time.sleep(sleep_sec)

    return raw_html_path, hourly_csv_path, daily_csv_path, len(hourly), len(daily)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="los-angeles")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--start_year", type=int, default=2015)
    parser.add_argument("--end_year", type=int, default=2024)
    parser.add_argument("--month", type=int, default=11)
    parser.add_argument("--extra_year", type=int, default=2024)
    parser.add_argument("--extra_month", type=int, default=12)
    parser.add_argument("--user_agent", default="DSCI510-FinalProject (xwang663@usc.edu)")
    args = parser.parse_args()

    make_folder(args.out)

    headers = {"User-Agent": args.user_agent}

    for y in range(args.start_year, args.end_year + 1):
        raw_path, hourly_path, daily_path, n_hourly, n_daily = run_one_month(
            args.city, y, args.month, args.out, headers
        )
        print(raw_path)
        print(hourly_path, n_hourly)
        print(daily_path, n_daily)

    raw_path, hourly_path, daily_path, n_hourly, n_daily = run_one_month(
        args.city, args.extra_year, args.extra_month, args.out, headers
    )
    print(raw_path)
    print(hourly_path, n_hourly)
    print(daily_path, n_daily)


if __name__ == "__main__":
    main()