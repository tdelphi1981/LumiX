"""Model source for the analyzers: an existing model (copied per run) or a factory."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Optional


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
        self._seen = {id(self.base)}
        self._keep = [self.base]       # keep ids stable while we compare them

    def new(self) -> Any:
        if self._factory is None:
            return deepcopy(self.base)
        model = self._factory()
        if id(model) in self._seen:
            raise ValueError(
                "model_factory must build a new model on every call; it returned a "
                "model it had already returned")
        self._seen.add(id(model))
        self._keep.append(model)
        return model
