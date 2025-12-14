import os
import json
import time
import argparse
import requests


def make_folder(p):
    if not os.path.exists(p):
        os.makedirs(p)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def save_csv(path, rows):
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return

    keys = sorted(list(rows[0].keys()))
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            line = []
            for k in keys:
                v = r.get(k)
                if v is None:
                    line.append("")
                else:
                    s = str(v).replace('"', '""')
                    if "," in s or "\n" in s:
                        s = f'"{s}"'
                    line.append(s)
            f.write(",".join(line) + "\n")


def fetch_one_page(token, station_id, start_date, end_date, offset, limit):
    url = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"
    headers = {"token": token}
    params = {
        "datasetid": "GHCND",
        "stationid": station_id,
        "startdate": start_date,
        "enddate": end_date,
        "units": "metric",
        "limit": limit,
        "offset": offset,
        "datatypeid": ["TMAX", "TMIN", "PRCP", "AWND"],
    }

    last_err = None
    for try_num in range(1, 6):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=120)
            if r.status_code != 200:
                raise RuntimeError(f"CDO error {r.status_code}: {r.text[:220]}")
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(2 * try_num)

    raise last_err


def pull_range(token, station_id, start_date, end_date):
    all_rows = []
    offset = 1
    limit = 1000

    while True:
        data = fetch_one_page(token, station_id, start_date, end_date, offset, limit)
        results = data.get("results", [])
        all_rows += results

        meta = data.get("metadata", {}).get("resultset", {})
        count = meta.get("count", 0)

        if offset + limit > count:
            break

        offset += limit
        time.sleep(0.25)

    return all_rows


def to_daily_table(rows):
    daily = {}

    for r in rows:
        d = r.get("date", "")[:10]
        t = r.get("datatype")
        v = r.get("value")

        if not d or not t:
            continue

        if d not in daily:
            daily[d] = {"date": d}

        daily[d][t] = v

    out = []
    for d in sorted(daily.keys()):
        out.append(daily[d])

    return out


def pull_many_small_ranges(token, station_id, start_year, end_year, month):
    all_rows = []
    for y in range(start_year, end_year + 1):
        start_date = f"{y}-{month:02d}-01"
        end_date = f"{y}-{month:02d}-30"
        part = pull_range(token, station_id, start_date, end_date)
        all_rows += part
        time.sleep(0.25)
    return all_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--station", default="GHCND:USW00023174")
    args = parser.parse_args()

    token = os.environ.get("NOAA_TOKEN")
    if not token:
        raise RuntimeError('Missing NOAA_TOKEN. Set it like: export NOAA_TOKEN="..."')

    make_folder(args.out)

    rows_hist = pull_many_small_ranges(token, args.station, 2015, 2024, 11)
    save_json(os.path.join(args.out, "cdo_hist_nov_2015_2024.json"), rows_hist)
    daily_hist = to_daily_table(rows_hist)
    save_csv(os.path.join(args.out, "cdo_hist_nov_2015_2024_daily.csv"), daily_hist)
    print("hist records:", len(rows_hist), "days:", len(daily_hist))

    rows_2024_nov = pull_range(token, args.station, "2024-11-01", "2024-11-30")
    rows_2024_dec = pull_range(token, args.station, "2024-12-01", "2024-12-31")
    rows_recent = rows_2024_nov + rows_2024_dec

    save_json(os.path.join(args.out, "cdo_nov_dec_2024.json"), rows_recent)
    daily_recent = to_daily_table(rows_recent)
    save_csv(os.path.join(args.out, "cdo_nov_dec_2024_daily.csv"), daily_recent)
    print("recent records:", len(rows_recent), "days:", len(daily_recent))

    print("saved in:", args.out)


if __name__ == "__main__":
    main()