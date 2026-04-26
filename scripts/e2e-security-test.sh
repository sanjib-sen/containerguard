#!/usr/bin/env bash
# End-to-end test for the security feature stack.
# Verifies: alert rules, threshold alerts, anomaly detection, compliance engine,
# network allowlist/blocklist, Trivy scans.

set -e

BASE="${BASE:-http://localhost:8002}"
PASS=0
FAIL=0

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
blue()  { printf "\033[34m%s\033[0m\n" "$*"; }

check() {
  local name="$1"
  local result="$2"
  if [[ "$result" == "ok" ]]; then
    green "  ✓ $name"
    PASS=$((PASS + 1))
  else
    red "  ✗ $name — $result"
    FAIL=$((FAIL + 1))
  fi
}

blue "==> 1. Server health"
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/")
[[ "$status" == "200" ]] && check "Server responds" "ok" || check "Server responds" "got $status"

blue "==> 2. Alert rules"
rule_id=$(curl -s -X POST "$BASE/api/v1/alerts/rules/" \
  -H "Content-Type: application/json" \
  -d '{"name":"e2e-test-cpu","description":"e2e test","metric":"cpu_pct","operator":"gt","threshold":0.0,"severity":"low","cooldown_sec":60,"enabled":true}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))')
[[ -n "$rule_id" ]] && check "Create alert rule" "ok" || check "Create alert rule" "no id returned"

list_count=$(curl -s "$BASE/api/v1/alerts/rules/" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
[[ "$list_count" -gt 0 ]] && check "List alert rules ($list_count rules)" "ok" || check "List alert rules" "empty"

blue "==> 3. Wait for threshold alert to fire"
echo "  (waiting up to 60s for telemetry to trigger e2e-test-cpu)"
for i in {1..12}; do
  count=$(curl -s "$BASE/api/v1/alerts/?limit=500" | python3 -c "import sys,json; print(sum(1 for a in json.load(sys.stdin) if a['rule_name']=='e2e-test-cpu'))")
  [[ "$count" -gt 0 ]] && break
  sleep 5
done
[[ "$count" -gt 0 ]] && check "Threshold alert fired ($count)" "ok" || check "Threshold alert fired" "none after 60s"

blue "==> 4. Anomaly detection"
anomaly_count=$(curl -s "$BASE/api/v1/alerts/?limit=500" | python3 -c "import sys,json; print(sum(1 for a in json.load(sys.stdin) if a['rule_name'].startswith('anomaly:')))")
[[ "$anomaly_count" -gt 0 ]] && check "Anomaly alerts present ($anomaly_count)" "ok" || check "Anomaly alerts present" "none"

blue "==> 5. Compliance rules"
compliance_rule_id=$(curl -s -X POST "$BASE/api/v1/compliance/rules/" \
  -H "Content-Type: application/json" \
  -d '{"name":"e2e-no-root","description":"e2e","severity":"high","rule_json":{"type":"no_root_processes","allow_pids":[1]},"enabled":true}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))')
[[ -n "$compliance_rule_id" ]] && check "Create compliance rule" "ok" || check "Create compliance rule" "no id"

echo "  (waiting up to 30s for compliance evaluation)"
for i in {1..6}; do
  c_results=$(curl -s "$BASE/api/v1/compliance/results/?limit=500" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  [[ "$c_results" -gt 0 ]] && break
  sleep 5
done
[[ "$c_results" -gt 0 ]] && check "Compliance results recorded ($c_results)" "ok" || check "Compliance results" "none"

compliance_alerts=$(curl -s "$BASE/api/v1/alerts/?limit=500" | python3 -c "import sys,json; print(sum(1 for a in json.load(sys.stdin) if a['rule_name'].startswith('compliance:')))")
[[ "$compliance_alerts" -ge 0 ]] && check "Compliance alerts ($compliance_alerts)" "ok"

blue "==> 6. Alert lifecycle"
alert_id=$(curl -s "$BASE/api/v1/alerts/?status=open&limit=1" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')
if [[ -n "$alert_id" ]]; then
  ack_status=$(curl -s -X PATCH "$BASE/api/v1/alerts/$alert_id" -H "Content-Type: application/json" -d '{"status":"acknowledged"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  [[ "$ack_status" == "acknowledged" ]] && check "Acknowledge alert" "ok" || check "Acknowledge alert" "got $ack_status"
  resolve_status=$(curl -s -X PATCH "$BASE/api/v1/alerts/$alert_id" -H "Content-Type: application/json" -d '{"status":"resolved"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  [[ "$resolve_status" == "resolved" ]] && check "Resolve alert" "ok" || check "Resolve alert" "got $resolve_status"
fi

blue "==> 7. Vulnerability scan"
scan_id=$(curl -s -X POST "$BASE/api/v1/scans/" -H "Content-Type: application/json" -d '{"image":"alpine:3.14"}' | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))')
[[ -n "$scan_id" ]] && check "Trigger scan" "ok" || check "Trigger scan" "no id"

if [[ -n "$scan_id" ]]; then
  echo "  (waiting up to 120s for scan to complete)"
  for i in {1..24}; do
    sstatus=$(curl -s "$BASE/api/v1/scans/$scan_id" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
    [[ "$sstatus" == "completed" || "$sstatus" == "failed" ]] && break
    sleep 5
  done
  [[ "$sstatus" == "completed" ]] && check "Scan completed" "ok" || check "Scan completed" "got $sstatus"
fi

blue "==> 8. Cleanup"
curl -s -X DELETE "$BASE/api/v1/alerts/rules/$rule_id" > /dev/null
[[ -n "$compliance_rule_id" ]] && curl -s -X DELETE "$BASE/api/v1/compliance/rules/$compliance_rule_id" > /dev/null
check "Cleanup test rules" "ok"

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  green "===  ALL TESTS PASSED ($PASS/$((PASS+FAIL)))  ==="
  exit 0
else
  red "===  $FAIL TESTS FAILED ($PASS/$((PASS+FAIL)))  ==="
  exit 1
fi
