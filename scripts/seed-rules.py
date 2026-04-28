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
    {"name": "Low Disk Space", "description": "Available disk space below 10%",
"metric": "disk_free_pct", "operator": "lt", "threshold": 10, "severity": "high",
"cooldown_sec": 600, "enabled": True},
    {"name": "Critical Disk Space", "description": "Available disk space below 5% — near full",
"metric": "disk_free_pct", "operator": "lt", "threshold": 5, "severity": "critical",
"cooldown_sec": 300, "enabled": True},
    {"name": "High Network Rx", "description": "Inbound network throughput unusually high",
"metric": "net_rx_bytes", "operator": "gt", "threshold": 500_000_000, "severity": "medium",
"cooldown_sec": 300, "enabled": True},
    {"name": "High Network Tx", "description": "Outbound network throughput unusually high",
"metric": "net_tx_bytes", "operator": "gt", "threshold": 500_000_000, "severity": "medium",
"cooldown_sec": 300, "enabled": True},
    {"name": "High Disk Read", "description": "Disk read rate elevated — possible runaway process",
"metric": "disk_read_bytes", "operator": "gt", "threshold": 1_000_000_000, "severity": "medium",
"cooldown_sec": 600, "enabled": True},
    {"name": "CPU Sustained > 95%", "description": "CPU pegged near ceiling — likely starving other workloads",
"metric": "cpu_pct", "operator": "gt", "threshold": 95, "severity": "critical",
"cooldown_sec": 120, "enabled": True},
    {"name": "High Open File Descriptors", "description": "Open FD count exceeds 80% of system limit",
"metric": "fd_open_pct", "operator": "gt", "threshold": 80, "severity": "high",
"cooldown_sec": 300, "enabled": True},
    {"name": "Process Count Spike", "description": "Total process count exceeds expected ceiling",
"metric": "proc_count", "operator": "gt", "threshold": 500, "severity": "medium",
"cooldown_sec": 300, "enabled": True},
    {"name": "Swap Usage > 50%", "description": "Swap usage exceeds 50% — memory pressure building",
"metric": "swap_pct", "operator": "gt", "threshold": 50, "severity": "medium",
"cooldown_sec": 300, "enabled": True},
    {"name": "Swap Usage > 80%", "description": "Swap usage critically high — OOM risk elevated",
"metric": "swap_pct", "operator": "gt", "threshold": 80, "severity": "critical",
"cooldown_sec": 120, "enabled": True},
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
    {"name": "no-world-writable-files", "description": "Flag world-writable files outside /tmp",
"severity": "high",
"rule_json": {"type": "file_permission_check", "mode_mask": "o+w", "exclude_paths": ["/tmp", "/var/tmp"]},
"enabled": True},
    {"name": "no-setuid-binaries", "description": "Disallow setuid/setgid binaries outside approved list",
"severity": "critical", "rule_json": {"type": "setuid_check",
"allowed_binaries": ["/usr/bin/sudo", "/usr/bin/su", "/usr/bin/passwd"]},
"enabled": True},
    {"name": "ssh-key-permissions", "description": "Enforce strict permissions on SSH private keys",
"severity": "high", "rule_json": {"type": "file_permission_check",
"paths": ["/root/.ssh", "/home/*/.ssh"], "max_mode": "0700"},
"enabled": True},
    {"name": "no-unauthorized-listeners", "description": "Block processes listening on non-approved ports",
"severity": "high", "rule_json": {"type": "port_allowlist", "allowed_ports": [80, 443, 8080, 8443, 22]},
"enabled": True},
    {"name": "immutable-audit-log", "description": "Audit log directory must not be modified or deleted",
"severity": "critical", "rule_json": {"type": "path_immutability", "paths": ["/var/log/audit"]},
"enabled": True},
    {"name": "no-package-manager-at-runtime", "description": "Block apt/yum/pip invocations in production containers",
"severity": "high", "rule_json": {"type": "process_denylist",
"binaries": ["apt", "apt-get", "yum", "dnf", "pip", "pip3"]},
"enabled": True},
    {"name": "no-shell-spawned-by-service", "description": "Prevent service processes from spawning interactive shells",
"severity": "critical", "rule_json": {"type": "child_process_denylist",
"parent_pattern": "^(gunicorn|uvicorn|node|java)", "child_binaries": ["bash", "sh", "zsh", "fish", "dash"]},
"enabled": True},
    {"name": "max-container-capabilities", "description": "Container must not hold dangerous Linux capabilities",
"severity": "critical", "rule_json": {"type": "capability_denylist",
"denied_caps": ["CAP_SYS_ADMIN", "CAP_NET_ADMIN", "CAP_SYS_PTRACE", "CAP_DAC_OVERRIDE", "CAP_SETUID"]},
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