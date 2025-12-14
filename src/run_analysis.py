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


def mean_std(vals):
    xs = [x for x in vals if x is not None]
    if not xs:
        return None, None
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    return m, v ** 0.5


def quantile(vals, q):
    xs = sorted([x for x in vals if x is not None])
    if not xs:
        return None
    if q <= 0:
        return xs[0]
    if q >= 1:
        return xs[-1]
    pos = (len(xs) - 1) * q
    left = int(pos)
    right = left + 1
    if right >= len(xs):
        return xs[left]
    frac = pos - left
    return xs[left] * (1 - frac) + xs[right] * frac


def pick_rows(rows, year=None, month=None, start=None, end=None):
    out = []
    for r in rows:
        d = r.get("date", "")
        if not d:
            continue
        if year is not None and d[:4] != str(year):
            continue
        if month is not None and d[5:7] != f"{month:02d}":
            continue
        if start is not None and d < start:
            continue
        if end is not None and d > end:
            continue
        out.append(r)
    return out


def save_csv(path, rows, keys):
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


def save_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/la_daily_cdo.csv")
    parser.add_argument("--out_folder", default="results")
    parser.add_argument("--z_cut", type=float, default=2.0)
    args = parser.parse_args()

    make_folder(args.out_folder)

    rows = read_csv(args.input)

    for r in rows:
        r["prcp_mm"] = to_float(r.get("prcp_mm"))
        r["prcp_z_nov"] = to_float(r.get("prcp_z_nov"))
        r["temp_avg_c"] = to_float(r.get("temp_avg_c"))

    hist_nov = []
    for r in rows:
        d = r.get("date", "")
        if not d:
            continue
        y = int(d[:4])
        m = int(d[5:7])
        if 2015 <= y <= 2024 and m == 11:
            hist_nov.append(r)

    hist_vals = [r["prcp_mm"] for r in hist_nov if r["prcp_mm"] is not None]
    m, s = mean_std(hist_vals)

    summary_lines = []
    summary_lines.append("Baseline (Nov 2015–2024) for LA daily precipitation (mm)")
    summary_lines.append(f"days_used: {len(hist_vals)}")
    summary_lines.append(f"mean_mm: {m}")
    summary_lines.append(f"std_mm: {s}")
    summary_lines.append(f"p50_mm: {quantile(hist_vals, 0.50)}")
    summary_lines.append(f"p75_mm: {quantile(hist_vals, 0.75)}")
    summary_lines.append(f"p90_mm: {quantile(hist_vals, 0.90)}")
    summary_lines.append(f"p95_mm: {quantile(hist_vals, 0.95)}")
    summary_lines.append("")

    nov_2024 = pick_rows(rows, year=2024, month=11)
    nov_2024_out = []
    for r in nov_2024:
        one = {}
        one["date"] = r.get("date")
        one["prcp_mm"] = r.get("prcp_mm")
        one["prcp_z_nov"] = r.get("prcp_z_nov")
        one["temp_avg_c"] = r.get("temp_avg_c")
        nov_2024_out.append(one)

    save_csv(
        os.path.join(args.out_folder, "nov_2024_daily.csv"),
        nov_2024_out,
        ["date", "prcp_mm", "prcp_z_nov", "temp_avg_c"],
    )

    big_days = []
    for r in nov_2024_out:
        z = r.get("prcp_z_nov")
        if z is not None and z >= args.z_cut:
            big_days.append(r)

    save_csv(
        os.path.join(args.out_folder, "nov_2024_anomaly_days.csv"),
        big_days,
        ["date", "prcp_mm", "prcp_z_nov", "temp_avg_c"],
    )

    summary_lines.append("Nov 2024 precipitation summary")
    nov_vals = [r["prcp_mm"] for r in nov_2024_out if r["prcp_mm"] is not None]
    summary_lines.append(f"days_used: {len(nov_vals)}")
    summary_lines.append(f"mean_mm: {mean_std(nov_vals)[0]}")
    summary_lines.append(f"total_mm: {sum(nov_vals) if nov_vals else None}")
    summary_lines.append(f"max_mm: {max(nov_vals) if nov_vals else None}")
    summary_lines.append("")
    summary_lines.append(f"Anomaly cutoff: z >= {args.z_cut}")
    summary_lines.append(f"anomaly_days_count: {len(big_days)}")
    if big_days:
        summary_lines.append("anomaly_days:")
        for r in big_days:
            summary_lines.append(f"- {r['date']} (mm={r['prcp_mm']}, z={r['prcp_z_nov']})")

    save_text(os.path.join(args.out_folder, "analysis_summary.txt"), "\n".join(summary_lines))

    print("saved:")
    print(os.path.join(args.out_folder, "analysis_summary.txt"))
    print(os.path.join(args.out_folder, "nov_2024_daily.csv"))
    print(os.path.join(args.out_folder, "nov_2024_anomaly_days.csv"))


if __name__ == "__main__":
    main()