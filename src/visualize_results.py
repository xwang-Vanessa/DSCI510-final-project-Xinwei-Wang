import os
import argparse
from datetime import datetime
import matplotlib.pyplot as plt


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
    s = str(x).strip()
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def to_date_num(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return None


def save_fig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/la_daily_cdo.csv")
    parser.add_argument("--out_folder", default="results/figures")
    args = parser.parse_args()

    make_folder(args.out_folder)

    rows = read_csv(args.input)

    data = []
    for r in rows:
        d = r.get("date")
        dt = to_date_num(d)
        if not dt:
            continue

        one = {}
        one["date"] = d
        one["dt"] = dt
        one["year"] = int(d[:4])
        one["month"] = int(d[5:7])

        one["temp_avg_c"] = to_float(r.get("temp_avg_c"))
        one["tmax_c"] = to_float(r.get("tmax_c"))
        one["tmin_c"] = to_float(r.get("tmin_c"))
        one["prcp_mm"] = to_float(r.get("prcp_mm"))
        one["prcp_z_nov"] = to_float(r.get("prcp_z_nov"))
        one["awnd_ms"] = to_float(r.get("awnd_ms"))
        one["temp_avg_c_roll7"] = to_float(r.get("temp_avg_c_roll7"))
        one["prcp_mm_roll7"] = to_float(r.get("prcp_mm_roll7"))

        data.append(one)

    data = sorted(data, key=lambda x: x["dt"])

    x_all = [r["dt"] for r in data]
    tmax = [r["tmax_c"] for r in data]
    tmin = [r["tmin_c"] for r in data]

    plt.figure()
    plt.plot(x_all, tmax, label="daily max (C)")
    plt.plot(x_all, tmin, label="daily min (C)")
    plt.title("Daily Temperature (TMAX/TMIN) - LA (CDO)")
    plt.xlabel("date")
    plt.ylabel("C")
    plt.legend()
    save_fig(os.path.join(args.out_folder, "temp_tmax_tmin.png"))

    pr = [r["prcp_mm"] for r in data]
    plt.figure()
    plt.plot(x_all, pr)
    plt.title("Daily Precipitation (mm) - LA (CDO)")
    plt.xlabel("date")
    plt.ylabel("mm")
    save_fig(os.path.join(args.out_folder, "precip_daily.png"))

    pr7 = [r["prcp_mm_roll7"] for r in data]
    plt.figure()
    plt.plot(x_all, pr7)
    plt.title("7-day Rolling Avg Precipitation (mm) - LA (CDO)")
    plt.xlabel("date")
    plt.ylabel("mm")
    save_fig(os.path.join(args.out_folder, "precip_roll7.png"))

    nov_rows = [r for r in data if r["month"] == 11 and 2015 <= r["year"] <= 2024]
    by_year = {}
    for r in nov_rows:
        y = r["year"]
        if y not in by_year:
            by_year[y] = []
        by_year[y].append(r["temp_avg_c"])

    years = sorted(by_year.keys())
    box_data = [by_year[y] for y in years]

    plt.figure()
    plt.boxplot(box_data, labels=[str(y) for y in years], showfliers=False)
    plt.title("November Temp Avg Distribution by Year (2015–2024)")
    plt.xlabel("year")
    plt.ylabel("temp avg (C)")
    plt.xticks(rotation=45)
    save_fig(os.path.join(args.out_folder, "box_nov_temp_by_year.png"))

    nov24 = [r for r in data if r["year"] == 2024 and r["month"] == 11]
    x_nov24 = [r["dt"] for r in nov24]
    z_nov24 = [r["prcp_z_nov"] for r in nov24]

    plt.figure()
    plt.plot(x_nov24, z_nov24)
    plt.axhline(2.0, linestyle="--")
    plt.title("Nov 2024 Precip Z-score (baseline: Nov 2015–2024)")
    plt.xlabel("date")
    plt.ylabel("z-score")
    save_fig(os.path.join(args.out_folder, "nov2024_precip_z.png"))

    temp = [r["temp_avg_c"] for r in data if r["temp_avg_c"] is not None and r["awnd_ms"] is not None]
    wind = [r["awnd_ms"] for r in data if r["temp_avg_c"] is not None and r["awnd_ms"] is not None]

    plt.figure()
    plt.scatter(temp, wind)
    plt.title("Temp Avg (C) vs Wind Speed (m/s) - LA (CDO)")
    plt.xlabel("temp avg (C)")
    plt.ylabel("wind (m/s)")
    save_fig(os.path.join(args.out_folder, "scatter_temp_vs_wind.png"))

    print("saved figures in:", args.out_folder)


if __name__ == "__main__":
    main()