"""Запити до SonarQube Web API (api/measures/component) і збереження сирих JSON-відповідей.

Для кожного компонента робить два запити:
  1) requested: metricKeys з лабораторної (class_complexity, coupling_between_objects, lcom4);
     SonarQube Community для Python таких метрик не має, тож очікувана відповідь сервера - помилка;
  2) supported: метрики, які сервер справді віддає (complexity, cognitive_complexity, ncloc, ...).
Токен береться зі змінної середовища SONAR_TOKEN (у файли й вивід не потрапляє).

Приклад:
    python scripts/sonar_api.py --label baseline --files app/services.py app/models.py --wait
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REQUESTED = "class_complexity,coupling_between_objects,lcom4"
SUPPORTED = "complexity,cognitive_complexity,ncloc,classes,functions,comment_lines_density"


def read_properties(path):
    props = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    return props


def auth_header(token):
    raw = base64.b64encode(f"{token}:".encode()).decode()
    return {"Authorization": "Basic " + raw}


def fetch(host, token, path, params):
    url = f"{host}{path}?{urllib.parse.urlencode(params, safe=',:/')}"
    request = urllib.request.Request(url, headers=auth_header(token))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", "replace")
    except urllib.error.URLError as err:
        raise SystemExit(f"Сервер {host} недоступний: {err.reason}")


def task_state(host, token, task_id):
    code, body = fetch(host, token, "/api/ce/task", {"id": task_id})
    return json.loads(body).get("task", {}).get("status", "") if code == 200 else ""


def wait_for_analysis(host, token, report_path=".scannerwork/report-task.txt", limit=120):
    if not Path(report_path).exists():
        print("Файлу .scannerwork/report-task.txt немає (скан у цьому запуску не виконувався): беремо останній аналіз сервера.")
        return ""
    task_id = read_properties(report_path).get("ceTaskId", "")
    for _ in range(limit // 3):
        state = task_state(host, token, task_id)
        if state in ("SUCCESS", "FAILED", "CANCELED"):
            print(f"Аналіз на сервері: {state}")
            return state
        time.sleep(3)
    print("Аналіз ще виконується, продовжуємо з тим, що є.")
    return ""


def curl_line(host, component, keys):
    query = urllib.parse.urlencode({"component": component, "metricKeys": keys}, safe=",:/")
    return f'curl -u %SONAR_TOKEN%: "{host}/api/measures/component?{query}"'


def save_raw(out_dir, label, index, kind, body):
    path = Path(out_dir) / f"{label}_{index}_{kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def query_component(host, token, component, keys):
    print(curl_line(host, component, keys))
    code, body = fetch(host, token, "/api/measures/component", {"component": component, "metricKeys": keys})
    print(f"  HTTP {code}: {body[:230]}")
    return code, body


def measures_of(body):
    data = json.loads(body).get("component", {})
    return {m["metric"]: m.get("value", "") for m in data.get("measures", [])}


def summary_row(component, body):
    values = measures_of(body)
    keys = ("complexity", "cognitive_complexity", "ncloc", "classes", "functions")
    return "| " + component + " | " + " | ".join(values.get(k, "-") for k in keys) + " |"


def run(args):
    token = os.environ.get("SONAR_TOKEN", "")
    props = read_properties(args.properties)
    host = args.host or props.get("sonar.host.url", "http://localhost:9000")
    project = props["sonar.projectKey"]
    if args.wait:
        wait_for_analysis(host, token)
    components = [project] + [f"{project}:{f.replace(chr(92), '/')}" for f in args.files]
    rows = []
    for index, component in enumerate(components):
        for kind, keys in (("requested", REQUESTED), ("supported", SUPPORTED)):
            code, body = query_component(host, token, component, keys)
            save_raw(args.out_dir, args.label, index, kind, body)
            if kind == "supported" and code == 200:
                rows.append(summary_row(component, body))
    print("\n| Компонент | complexity | cognitive | ncloc | classes | functions |\n| --- | --- | --- | --- | --- | --- |")
    print("\n".join(rows))
    return 0


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--properties", default="sonar-project.properties")
    ap.add_argument("--host")
    ap.add_argument("--out-dir", default="reports/sonar")
    ap.add_argument("--wait", action="store_true")
    return ap.parse_args()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run(parse_args()))
