from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..db import DataAccessLayer, get_dal
from ..schemas import (
    AlertActionRequest,
    AlertResponse,
    AlertRuleCreateRequest,
    AlertRuleResponse,
    AlertRuleUpdateRequest,
)

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    responses={404: {"description": "Not found"}},
)


# ── Alerts ──

@router.get("/", response_model=list[AlertResponse])
async def listAlerts(
    dal: DataAccessLayer = Depends(get_dal),
    agent_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None, description="open / acknowledged / resolved"),
    severity: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
):
    alerts = await dal.alerts.list_alerts(
        agent_id=agent_id,
        status=status,
        severity=severity,
        limit=limit,
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
async def getAlert(alert_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    alert = await dal.alerts.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
async def updateAlertStatus(
    alert_id: UUID,
    payload: AlertActionRequest,
    dal: DataAccessLayer = Depends(get_dal),
):
    if payload.status not in {"open", "acknowledged", "resolved"}:
        raise HTTPException(status_code=400, detail="status must be open, acknowledged, or resolved")
    alert = await dal.alerts.set_alert_status(alert_id, payload.status)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


# ── Alert Rules ──

@router.get("/rules/", response_model=list[AlertRuleResponse])
async def listRules(dal: DataAccessLayer = Depends(get_dal)):
    rules = await dal.alerts.list_rules()
    return [AlertRuleResponse.model_validate(r) for r in rules]


@router.post("/rules/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def createRule(payload: AlertRuleCreateRequest, dal: DataAccessLayer = Depends(get_dal)):
    if payload.operator not in {"gt", "ge", "lt", "le", "eq", "ne"}:
        raise HTTPException(status_code=400, detail="invalid operator")
    if payload.severity not in {"low", "medium", "high", "critical"}:
        raise HTTPException(status_code=400, detail="invalid severity")
    rule = await dal.alerts.create_rule(
        name=payload.name,
        description=payload.description,
        metric=payload.metric,
        operator=payload.operator,
        threshold=payload.threshold,
        severity=payload.severity,
        cooldown_sec=payload.cooldown_sec,
        enabled=payload.enabled,
    )
    return AlertRuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def updateRule(
    rule_id: UUID,
    payload: AlertRuleUpdateRequest,
    dal: DataAccessLayer = Depends(get_dal),
):
    rule = await dal.alerts.update_rule(rule_id, **payload.model_dump(exclude_unset=True))
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return AlertRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deleteRule(rule_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    deleted = await dal.alerts.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
