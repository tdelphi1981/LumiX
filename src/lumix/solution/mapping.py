"""Solution mapping utilities for LumiX."""

from typing import Any, Dict, Generic, List, TypeVar

from ..core.variables import LXVariable

TModel = TypeVar("TModel")


class LXSolutionMapper(Generic[TModel]):
    """
    Maps solution values back to ORM model instances.

    Handles:
    - Single-indexed variables
    - Multi-indexed variables
    - Join-based variables
    """

    def map_variable_to_models(
        self,
        var: LXVariable[TModel, Any],
        solution_values: Dict[Any, float],
        model_instances: List[TModel],
    ) -> Dict[TModel, float]:
        """
        Map variable values to model instances.

        Args:
            var: LXVariable definition
            solution_values: Solution values (index -> value)
            model_instances: Model instances used in optimization

        Returns:
            Dictionary mapping model instances to values
        """
        if var.index_func is None:
            return {}

        result = {}
        for instance in model_instances:
            key = var.index_func(instance)
            if key in solution_values:
                result[instance] = solution_values[key]

        return result

    def map_multi_indexed_variable(
        self,
        var: LXVariable,
        solution_values: Dict[tuple, float],
    ) -> Dict[tuple, float]:
        """
        Map multi-indexed variable values to model instance tuples.

        Args:
            var: LXVariable definition
            solution_values: Solution values ((key1, key2, ...) -> value)

        Returns:
            Dictionary mapping model instance tuples to values
        """
        # Check if variable has cartesian product
        if var._cartesian is None or not var._cartesian.dimensions:
            return {}

        # Retrieve instances automatically from each dimension
        model_instances_by_dim = [dim.get_instances() for dim in var._cartesian.dimensions]

        # Build reverse mappings for each dimension: key -> model_instance
        reverse_maps = []
        for dim, instances in zip(var._cartesian.dimensions, model_instances_by_dim):
            # Create mapping using the dimension's key function
            key_to_instance = {dim.key_func(inst): inst for inst in instances}
            reverse_maps.append(key_to_instance)

        # Transform solution values from key tuples to instance tuples
        result = {}
        for key_tuple, value in solution_values.items():
            try:
                # Map each key to its corresponding model instance
                instance_tuple = tuple(
                    reverse_maps[i][key] for i, key in enumerate(key_tuple)
                )
                result[instance_tuple] = value
            except (KeyError, IndexError):
                # Skip entries where mapping fails (data inconsistency)
                continue

        return result


__all__ = ["LXSolutionMapper"]
