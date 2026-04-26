"""
Compliance engine: evaluates JSON-predicate compliance rules against incoming telemetry.

Supported predicate types (in rule_json["type"]):
  - "no_root_processes":      No process with user='root' allowed (use rule_json["allow_pids"]=[1] for shims)
  - "no_unauthorized_ports":  Listening ports must be in rule_json["allowed_ports"]
  - "no_sensitive_paths":     Filesystem events on rule_json["paths"] forbidden
  - "network_allowlist":      Outbound dst_ip must be in rule_json["allowed_ips"] (or match "allowed_cidrs")
  - "network_blocklist":      Outbound dst_ip must NOT be in rule_json["blocked_ips"]
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any
from uuid import UUID

from ..db.models import Agent, ComplianceRules
from ..db.repository.alertsRepo import AlertsRepository
from ..db.repository.complianceRepo import ComplianceRepository
from ..metrics.exporter import record_compliance_evaluation
from ..schemas import TelemetryIngestRequest
from .alerts import alert_engine

logger = logging.getLogger(__name__)


class ComplianceEngine:

    async def evaluate(
        self,
        agent: Agent,
        payload: TelemetryIngestRequest,
        compliance_repo: ComplianceRepository,
        alerts_repo: AlertsRepository,
    ) -> list[tuple[ComplianceRules, str, dict[str, Any]]]:
        """Evaluate all enabled rules against telemetry. Returns list of (rule, status, details)."""
        rules = await compliance_repo.list_rules(enabled_only=True)
        results: list[tuple[ComplianceRules, str, dict[str, Any]]] = []

        for rule in rules:
            try:
                status, details = self._evaluate_rule(rule, payload)
            except Exception as exc:
                logger.exception("compliance rule %s eval failed", rule.name)
                status = "error"
                details = {"error": str(exc)}

            await compliance_repo.record_result(
                agent_id=agent.id,
                rule_id=rule.id,
                status=status,
                details=details,
            )
            record_compliance_evaluation(status)

            if status == "fail":
                # Fire an alert for the violation
                msg = f"Compliance violation: {rule.name} on {agent.hostname} — {details.get('summary', '')}"
                await alert_engine.fire_custom(
                    alerts_repo,
                    agent=agent,
                    rule_id=rule.id,
                    rule_name=f"compliance:{rule.name}",
                    severity=rule.severity,
                    message=msg,
                    cooldown_key=f"compliance:{rule.id}",
                    cooldown_sec=300,
                    metadata={
                        "type": "compliance",
                        "rule_name": rule.name,
                        "rule_type": rule.rule_json.get("type"),
                        **details,
                    },
                )

            results.append((rule, status, details))

        return results

    def _evaluate_rule(
        self,
        rule: ComplianceRules,
        payload: TelemetryIngestRequest,
    ) -> tuple[str, dict[str, Any]]:
        rule_json = rule.rule_json or {}
        rule_type = rule_json.get("type")

        if rule_type == "no_root_processes":
            allow_pids = set(rule_json.get("allow_pids", []))
            offenders = [
                {"pid": p.pid, "command": p.command, "user": p.user}
                for p in payload.processes
                if p.user == "root" and p.pid not in allow_pids
            ]
            if offenders:
                return "fail", {
                    "summary": f"{len(offenders)} root processes detected",
                    "offenders": offenders[:10],
                }
            return "pass", {"summary": "No unauthorized root processes"}

        if rule_type == "no_unauthorized_ports":
            allowed = set(rule_json.get("allowed_ports", []))
            offenders = [
                {"port": p.port, "protocol": p.protocol, "process": p.process}
                for p in payload.ports
                if p.port not in allowed
            ]
            if offenders:
                return "fail", {
                    "summary": f"{len(offenders)} unauthorized open ports",
                    "offenders": offenders[:10],
                }
            return "pass", {"summary": "All open ports authorized"}

        if rule_type == "no_sensitive_paths":
            sensitive = set(rule_json.get("paths", ["/etc/shadow", "/etc/passwd", "/root"]))
            if payload.filesystem is None:
                return "pass", {"summary": "No filesystem events"}
            offenders = []
            for evt in payload.filesystem.events:
                for sp in sensitive:
                    if evt.path.startswith(sp):
                        offenders.append({
                            "type": evt.type,
                            "path": evt.path,
                            "process": evt.process,
                        })
                        break
            if offenders:
                return "fail", {
                    "summary": f"{len(offenders)} accesses to sensitive paths",
                    "offenders": offenders[:10],
                }
            return "pass", {"summary": "No sensitive path access"}

        if rule_type == "network_allowlist":
            if payload.network is None:
                return "pass", {"summary": "No network activity"}
            allowed_ips = set(rule_json.get("allowed_ips", []))
            allowed_cidrs = [ipaddress.ip_network(c, strict=False) for c in rule_json.get("allowed_cidrs", [])]
            offenders = []
            for conn in payload.network.connections:
                if conn.direction != "outbound" or conn.dst_ip is None:
                    continue
                ip_str = str(conn.dst_ip)
                if ip_str in allowed_ips:
                    continue
                ip_obj = conn.dst_ip
                if any(ip_obj in c for c in allowed_cidrs):
                    continue
                offenders.append({"dst_ip": ip_str, "dst_port": conn.dst_port, "protocol": conn.protocol})
            if offenders:
                return "fail", {
                    "summary": f"{len(offenders)} non-allowlisted outbound connections",
                    "offenders": offenders[:10],
                }
            return "pass", {"summary": "All outbound traffic allowlisted"}

        if rule_type == "network_blocklist":
            if payload.network is None:
                return "pass", {"summary": "No network activity"}
            blocked_ips = set(rule_json.get("blocked_ips", []))
            blocked_cidrs = [ipaddress.ip_network(c, strict=False) for c in rule_json.get("blocked_cidrs", [])]
            offenders = []
            for conn in payload.network.connections:
                if conn.direction != "outbound" or conn.dst_ip is None:
                    continue
                ip_str = str(conn.dst_ip)
                ip_obj = conn.dst_ip
                if ip_str in blocked_ips or any(ip_obj in c for c in blocked_cidrs):
                    offenders.append({"dst_ip": ip_str, "dst_port": conn.dst_port, "protocol": conn.protocol})
            if offenders:
                return "fail", {
                    "summary": f"{len(offenders)} blocked outbound connections",
                    "offenders": offenders[:10],
                }
            return "pass", {"summary": "No traffic to blocked targets"}

        return "skip", {"summary": f"Unknown rule type: {rule_type}"}


compliance_engine = ComplianceEngine()
