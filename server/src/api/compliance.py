from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..db import DataAccessLayer, get_dal
from ..schemas import (
    ComplianceResultResponse,
    ComplianceRuleCreateRequest,
    ComplianceRuleResponse,
)

router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
    responses={404: {"description": "Not found"}},
)


@router.get("/rules/", response_model=list[ComplianceRuleResponse])
async def listRules(dal: DataAccessLayer = Depends(get_dal)):
    rules = await dal.compliance.list_rules()
    return [ComplianceRuleResponse.model_validate(r) for r in rules]


@router.post("/rules/", response_model=ComplianceRuleResponse, status_code=status.HTTP_201_CREATED)
async def createRule(payload: ComplianceRuleCreateRequest, dal: DataAccessLayer = Depends(get_dal)):
    if payload.severity not in {"low", "medium", "high", "critical"}:
        raise HTTPException(status_code=400, detail="invalid severity")
    if "type" not in payload.rule_json:
        raise HTTPException(status_code=400, detail="rule_json must include 'type' field")
    rule = await dal.compliance.create_rule(
        name=payload.name,
        description=payload.description,
        rule_json=payload.rule_json,
        severity=payload.severity,
        enabled=payload.enabled,
    )
    return ComplianceRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deleteRule(rule_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    deleted = await dal.compliance.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")


@router.get("/results/", response_model=list[ComplianceResultResponse])
async def listResults(
    dal: DataAccessLayer = Depends(get_dal),
    agent_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
):
    results = await dal.compliance.list_results(agent_id=agent_id, limit=limit)
    return [ComplianceResultResponse.model_validate(r) for r in results]


@router.get("/status/", response_model=list[ComplianceResultResponse])
async def latestStatus(dal: DataAccessLayer = Depends(get_dal)):
    """Latest compliance result per (agent, rule)."""
    results = await dal.compliance.latest_per_agent_per_rule()
    return [ComplianceResultResponse.model_validate(r) for r in results]
