import os
import argparse
from datetime import datetime


def make_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


def split_csv_line(line, want_cols):
    out = []
    cur = ""
    in_q = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_q and i + 1 < len(line) and line[i + 1] == '"':
                cur += '"'
                i += 1
            else:
                in_q = not in_q
        elif ch == "," and not in_q:
            out.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    out.append(cur)
    while len(out) < want_cols:
        out.append("")
    return out


def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines:
        return []
    header = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        parts = split_csv_line(line, len(header))
        r = {}
        for i, k in enumerate(header):
            r[k] = parts[i] if i < len(parts) else ""
        rows.append(r)
    return rows


def to_float(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        return None


def merge_daily_rows(rows_list):
    daily = {}
    for rows in rows_list:
        for r in rows:
            d = parse_date(r.get("date", ""))
            if not d:
                continue
            if d not in daily:
                daily[d] = {"date": d}

            for k, v in r.items():
                if k == "date":
                    continue
                if k in ["TMAX", "TMIN", "PRCP", "AWND"]:
                    num = to_float(v)
                    if num is not None:
                        daily[d][k] = num

    out = []
    for d in sorted(daily.keys()):
        out.append(daily[d])
    return out


def add_features(rows):
    for r in rows:
        tmax = r.get("TMAX")
        tmin = r.get("TMIN")
        prcp = r.get("PRCP")
        awnd = r.get("AWND")

        if tmax is not None:
            r["tmax_c"] = tmax / 10.0
        else:
            r["tmax_c"] = None

        if tmin is not None:
            r["tmin_c"] = tmin / 10.0
        else:
            r["tmin_c"] = None

        if tmax is not None and tmin is not None:
            r["temp_range_c"] = (tmax - tmin) / 10.0
            r["temp_avg_c"] = (tmax + tmin) / 20.0
        else:
            r["temp_range_c"] = None
            r["temp_avg_c"] = None

        if prcp is None:
            r["prcp_mm"] = 0.0
        else:
            r["prcp_mm"] = prcp / 10.0

        if awnd is not None:
            r["awnd_ms"] = awnd / 10.0
        else:
            r["awnd_ms"] = None

        r["year"] = int(r["date"][:4])
        r["month"] = int(r["date"][5:7])

    return rows


def rolling_avg(values, window):
    out = []
    for i in range(len(values)):
        left = i - window + 1
        if left < 0:
            left = 0
        chunk = [x for x in values[left : i + 1] if x is not None]
        out.append((sum(chunk) / len(chunk)) if chunk else None)
    return out


def add_rolling(rows, key, window, new_key):
    vals = [r.get(key) for r in rows]
    roll = rolling_avg(vals, window)
    for i in range(len(rows)):
        rows[i][new_key] = roll[i]
    return rows


def mean_std(vals):
    xs = [x for x in vals if x is not None]
    if not xs:
        return None, None
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    return m, v ** 0.5


def add_month_baseline_z(rows, key, month, z_key):
    base_vals = []
    for r in rows:
        if r.get("month") == month and r.get(key) is not None:
            if 2015 <= r.get("year", 0) <= 2024:
                base_vals.append(r.get(key))

    m, s = mean_std(base_vals)

    for r in rows:
        x = r.get(key)
        if x is None or m is None or s is None or s == 0:
            r[z_key] = None
        else:
            r[z_key] = (x - m) / s

    return rows


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
                v = r.get(k)
                if v is None:
                    parts.append("")
                else:
                    s = str(v).replace('"', '""')
                    if "," in s or "\n" in s:
                        s = f'"{s}"'
                    parts.append(s)
            f.write(",".join(parts) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_folder", default="data/raw")
    parser.add_argument("--processed_folder", default="data/processed")
    args = parser.parse_args()

    make_folder(args.processed_folder)

    p1 = os.path.join(args.raw_folder, "cdo_hist_nov_2015_2024_daily.csv")
    p2 = os.path.join(args.raw_folder, "cdo_nov_dec_2024_daily.csv")

    rows1 = read_csv(p1)
    rows2 = read_csv(p2)

    daily = merge_daily_rows([rows1, rows2])
    daily = add_features(daily)

    daily = add_rolling(daily, "temp_avg_c", 7, "temp_avg_c_roll7")
    daily = add_rolling(daily, "prcp_mm", 7, "prcp_mm_roll7")
    daily = add_rolling(daily, "temp_avg_c", 14, "temp_avg_c_roll14")
    daily = add_rolling(daily, "prcp_mm", 14, "prcp_mm_roll14")

    daily = add_month_baseline_z(daily, "prcp_mm", 11, "prcp_z_nov")

    out_path = os.path.join(args.processed_folder, "la_daily_cdo.csv")
    save_csv(out_path, daily)

    print(out_path)
    print("days:", len(daily))


if __name__ == "__main__":
    main()