import json, math, statistics, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

url, n, conc, label = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]

def hit(_):
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            r.read()
            ok = r.status == 200
    except Exception:
        ok = False
    return (time.perf_counter() - start) * 1000, ok

with ThreadPoolExecutor(conc) as ex:
    list(ex.map(hit, range(30)))          # warm-up, not counted
    res = list(ex.map(hit, range(n)))
lat = sorted(x for x, _ in res)
pct = lambda q: lat[max(0, math.ceil(q * len(lat)) - 1)]
err = sum(1 for _, ok in res if not ok)
print(json.dumps({"label": label, "n": n, "mean": round(statistics.mean(lat), 1),
                  "p50": round(pct(.5), 1), "p95": round(pct(.95), 1),
                  "p99": round(pct(.99), 1), "max": round(lat[-1], 1),
                  "error_rate_pct": round(100 * err / n, 2)}))
