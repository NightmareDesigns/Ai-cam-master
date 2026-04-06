"""Alert rules API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.alert_rule import AlertRule
from src.schemas.alert_rule import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _get_or_404(rule_id: int, db: Session) -> AlertRule:
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return rule


@router.get("/", response_model=List[AlertRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return db.query(AlertRule).order_by(AlertRule.id).all()


@router.post("/", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)):
    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=AlertRuleRead)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    return _get_or_404(rule_id, db)


@router.patch("/{rule_id}", response_model=AlertRuleRead)
def update_rule(rule_id: int, payload: AlertRuleUpdate, db: Session = Depends(get_db)):
    rule = _get_or_404(rule_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = _get_or_404(rule_id, db)
    db.delete(rule)
    db.commit()
