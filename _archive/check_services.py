import urllib.request
import sys

for name, url in [
    ("auth-service", "http://localhost:3001/health"),
    ("api-gateway", "http://localhost:3000/health"),
]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            print(f"{name}: OK ({resp.status})")
    except Exception as e:
        print(f"{name}: {e}")
