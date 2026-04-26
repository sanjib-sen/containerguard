"""Seed baseline alert + compliance rules. Idempotent: skips rules that already exist."""

import json
import os
import urllib.request

BASE = os.environ.get("BASE", "http://localhost:8002")

ALERT_RULES = [
    {"name": "High CPU", "description": "CPU usage exceeds 80%",
     "metric": "cpu_pct", "operator": "gt", "threshold": 80, "severity": "high",
     "cooldown_sec": 300, "enabled": True},
    {"name": "Memory > 80%", "description": "Memory usage exceeds 80% of container limit",
     "metric": "mem_pct", "operator": "gt", "threshold": 80, "severity": "high",
     "cooldown_sec": 300, "enabled": True},
    {"name": "Memory > 90%", "description": "Memory usage exceeds 90% — near OOM",
     "metric": "mem_pct", "operator": "gt", "threshold": 90, "severity": "critical",
     "cooldown_sec": 120, "enabled": True},
    {"name": "High Disk Write", "description": "Disk write rate elevated",
     "metric": "disk_write_bytes", "operator": "gt", "threshold": 1_000_000_000, "severity": "medium",
     "cooldown_sec": 600, "enabled": True},
]

COMPLIANCE_RULES = [
    {"name": "no-root-processes", "description": "Disallow root processes (except PID 1)",
     "severity": "high",
     "rule_json": {"type": "no_root_processes", "allow_pids": [1]},
     "enabled": True},
    {"name": "no-sensitive-paths", "description": "Block reads/writes on sensitive system paths",
     "severity": "critical",
     "rule_json": {"type": "no_sensitive_paths",
                   "paths": ["/etc/shadow", "/etc/passwd", "/root", "/etc/sudoers"]},
     "enabled": True},
    {"name": "internal-network-only", "description": "Outbound connections must stay in private CIDRs",
     "severity": "high",
     "rule_json": {"type": "network_allowlist",
                   "allowed_cidrs": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"]},
     "enabled": True},
]


def get_json(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.loads(r.read())


def post_json(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def seed(category, path, rules):
    existing_names = {r["name"] for r in get_json(path)}
    print(f"Seeding {category} rules:")
    for rule in rules:
        if rule["name"] in existing_names:
            print(f"  · {rule['name']} (already exists)")
        else:
            post_json(path, rule)
            print(f"  + {rule['name']}")


seed("alert", "/api/v1/alerts/rules/", ALERT_RULES)
seed("compliance", "/api/v1/compliance/rules/", COMPLIANCE_RULES)
print("Done.")
