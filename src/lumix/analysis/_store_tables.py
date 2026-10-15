"""SQLAlchemy tables of :class:`lumix.analysis.store.LXResultStore` (imported lazily)."""
from __future__ import annotations

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String)
from sqlalchemy.orm import declarative_base

LXResultBase = declarative_base()


class LXRunRow(LXResultBase):
    __tablename__ = "lumix_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis = Column(String(255), nullable=True, index=True)
    scenario = Column(String(255), nullable=False)
    status = Column(String(64), nullable=False)
    objective = Column(Float, nullable=True)
    solve_time = Column(Float, nullable=True)
    modifications = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False)


class LXRunValueRow(LXResultBase):
    __tablename__ = "lumix_run_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("lumix_runs.id", ondelete="CASCADE"),
                    nullable=False, index=True)
    kind = Column(String(16), nullable=False)        # value | shadow_price | reduced_cost
    name = Column(String(255), nullable=False)       # variable or constraint family
    indexed = Column(Boolean, nullable=False)
    key = Column(JSON, nullable=True)
    value = Column(Float, nullable=True)
