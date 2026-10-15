"""Model source for the analyzers: an existing model (copied per run) or a factory."""
from __future__ import annotations

import weakref
from copy import deepcopy
from typing import Any, Callable, Dict, Optional


def _parts(model: Any) -> Dict[int, Any]:
    """Constraint and variable objects of a model, by identity."""
    return {id(o): o for o in (*model.constraints, *model.variables)}


class ModelSource:
    """Hands out an independent model per run, either by deep-copying a base model or by
    calling the user's factory (which must build a new model on every call)."""

    def __init__(self, model: Any, factory: Optional[Callable[[], Any]],
                 optimizer: Any, owner: str):
        if optimizer is None:
            raise TypeError(f"{owner} needs an optimizer")
        if (model is None) == (factory is None):
            raise ValueError(
                f"{owner} needs exactly one of a model or model_factory")
        self._factory = factory
        self.base = model if model is not None else factory()
        # Weak references: a built model (and the session its data came from) is freed
        # once its run is over; a model still alive cannot share its id with a new one.
        self._seen: Dict[int, "weakref.ref[Any]"] = {id(self.base): weakref.ref(self.base)}

    def new(self) -> Any:
        if self._factory is None:
            return deepcopy(self.base)
        model = self._factory()
        ref = self._seen.get(id(model))
        if ref is not None and ref() is model:
            raise ValueError(
                "model_factory must build a new model on every call; it returned a "
                "model it had already returned")
        base_parts = _parts(self.base)
        shared = [o for i, o in _parts(model).items() if i in base_parts]
        if shared:
            raise ValueError(
                "model_factory must build new constraints and variables on every call; "
                f"the new model shares {len(shared)} object(s) with the base model "
                f"(e.g. '{shared[0].name}'), so a what-if or scenario change would "
                "modify the base model")
        self._seen = {k: r for k, r in self._seen.items() if r() is not None}
        self._seen[id(model)] = weakref.ref(model)
        return model
