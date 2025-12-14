import requests

url = "https://www.timeanddate.com/weather/usa/los-angeles/historic?month=11&year=2024"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

r = requests.get(url, headers=headers, timeout=30)
print("status:", r.status_code)
print(r.text[:500])