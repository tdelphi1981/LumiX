"""Persist scenario and what-if results to a database (SQLAlchemy).

.. versionadded:: 0.3.0

Example::

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from lumix import LXResultStore, LXScenarioAnalyzer

    engine = create_engine("sqlite:///results.db")
    LXResultStore.create_tables(engine)
    with Session(engine) as session:              # a session of its own for the store
        store = LXResultStore(session, analysis="q3-capacity")
        analyzer = LXScenarioAnalyzer(optimizer=optimizer, model_factory=build_model,
                                      result_store=store)
        analyzer.add_scenario(...)
        analyzer.run_all_scenarios()          # one lumix_runs row per solve
        for run in store.runs(analysis="q3-capacity"):
            print(run.scenario, run.objective, store.values(run.id))
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

KINDS = ("value", "shadow_price", "reduced_cost")


@dataclass(frozen=True)
class LXStoredRun:
    """One recorded solve (a row of ``lumix_runs``)."""

    id: int
    analysis: Optional[str]
    scenario: str
    status: str
    objective: Optional[float]           # None when the run is not feasible
    solve_time: Optional[float]
    modifications: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[_dt.datetime] = None


def _tables():
    try:
        from . import _store_tables
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise ImportError(
            "LXResultStore needs SQLAlchemy: pip install 'lumix-opt[orm]'") from exc
    return _store_tables


def _encode_key(key: Any) -> Any:
    if key is None or isinstance(key, (bool, int, float, str)):
        return key
    if isinstance(key, (tuple, list)):
        return [_encode_key(k) for k in key]
    return str(key)


def _decode_key(key: Any) -> Any:
    if isinstance(key, list):
        return tuple(_decode_key(k) for k in key)
    return key


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return repr(value)


class LXResultStore:
    """Writes every analyzer solve to the ``lumix_runs`` / ``lumix_run_values`` tables.

    Args:
        session: A SQLAlchemy ``Session``.
        analysis: Label stored on every run (filter with :meth:`runs`).
        include_sensitivity: Also store shadow prices and reduced costs (LP solves with
            ``enable_sensitivity()``).
        commit: Commit after each recorded run (default). With False the rows are only
            flushed and the caller commits. ``session.commit()`` commits everything
            pending in the session, not only LumiX rows, and with SQLAlchemy's default
            ``expire_on_commit=True`` expires every instance loaded in it. Give the store
            its own session, or pass ``commit=False`` and commit yourself.
    """

    def __init__(self, session: Any, analysis: Optional[str] = None,
                 include_sensitivity: bool = False, commit: bool = True):
        self._t = _tables()
        self.session = session
        self.analysis = analysis
        self.include_sensitivity = include_sensitivity
        self.commit = commit

    @staticmethod
    def create_tables(bind: Any) -> None:
        """Create the two LumiX tables on an engine or connection (no-op if present)."""
        _tables().LXResultBase.metadata.create_all(bind)

    def record(self, scenario: str, solution: Any, model: Any = None,
               modifications: Sequence[Mapping[str, Any]] = ()) -> int:
        """Store one solve; returns the new run id."""
        t = self._t
        run = t.LXRunRow(
            analysis=self.analysis, scenario=scenario, status=solution.status,
            objective=float(solution.objective_value) if solution.is_feasible() else None,
            solve_time=solution.solve_time,
            modifications=[_jsonable(dict(m)) for m in modifications],
            created_at=_dt.datetime.now(_dt.timezone.utc))
        self.session.add(run)
        self.session.flush()
        rows = self._value_rows(run.id, solution, model)
        self.session.add_all(rows)
        if self.commit:
            self.session.commit()
        else:
            self.session.flush()
        return run.id

    def _value_rows(self, run_id: int, solution: Any, model: Any) -> list:
        from .sensitivity import _constraint_rows, _variable_entries
        t = self._t

        def row(kind, name, indexed, key, value):
            return t.LXRunValueRow(run_id=run_id, kind=kind, name=name, indexed=indexed,
                                   key=_encode_key(key),
                                   value=None if value is None else float(value))

        out = []
        if solution.is_feasible():
            for name, val in solution.variables.items():
                for key, _entry, value in _variable_entries(name, val):
                    out.append(row("value", name, isinstance(val, dict), key, value))
        if self.include_sensitivity:
            for name, val in solution.variables.items():
                for key, entry, _v in _variable_entries(name, val):
                    rc = solution.reduced_costs.get(entry)
                    if rc is not None:
                        out.append(row("reduced_cost", name, isinstance(val, dict), key, rc))
            if model is not None:
                for c in model.constraints:
                    for key, row_name in _constraint_rows(c):
                        price = solution.shadow_prices.get(row_name)
                        if price is not None:
                            out.append(row("shadow_price", c.name,
                                           c.index_func is not None, key, price))
            else:
                for row_name, price in solution.shadow_prices.items():
                    out.append(row("shadow_price", row_name, False, None, price))
        return out

    def runs(self, analysis: Optional[str] = None) -> List[LXStoredRun]:
        """Recorded runs in insertion order, optionally only one analysis label."""
        t = self._t
        query = self.session.query(t.LXRunRow)
        if analysis is not None:
            query = query.filter(t.LXRunRow.analysis == analysis)
        return [LXStoredRun(id=r.id, analysis=r.analysis, scenario=r.scenario,
                            status=r.status, objective=r.objective,
                            solve_time=r.solve_time, modifications=list(r.modifications),
                            created_at=r.created_at)
                for r in query.order_by(t.LXRunRow.id)]

    def values(self, run_id: int,
               kind: str = "value") -> Dict[str, Union[float, Dict[Any, float]]]:
        """Stored values of one run, shaped like ``LXSolution.variables``:
        ``{name: value}`` for scalars, ``{name: {key: value}}`` for indexed families.

        Index keys are stored as JSON: ``None``, bool, int, float, str and tuples of
        them round-trip (tuples come back as tuples); any other key is stored as
        ``str(key)``, so keys with equal ``str()`` come back as one entry. Index by a
        JSON-friendly id (``lambda p: p.id``)."""
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
        t = self._t
        out: Dict[str, Union[float, Dict[Any, float]]] = {}
        rows = (self.session.query(t.LXRunValueRow)
                .filter(t.LXRunValueRow.run_id == run_id, t.LXRunValueRow.kind == kind)
                .order_by(t.LXRunValueRow.id))
        for r in rows:
            if r.indexed:
                out.setdefault(r.name, {})[_decode_key(r.key)] = r.value  # type: ignore[index]
            else:
                out[r.name] = r.value
        return out


__all__ = ["LXResultStore", "LXStoredRun"]
