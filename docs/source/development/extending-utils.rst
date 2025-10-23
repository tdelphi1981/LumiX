Extending Utils Components
===========================

Guide for extending and customizing LumiX utils components.

Overview
--------

The utils module is designed to be extensible. This guide shows how to:

- Create custom loggers for specific domains
- Define custom ORM protocols
- Add new rational approximation algorithms
- Build domain-specific utilities

Extending the Logger
--------------------

Custom Logger Classes
~~~~~~~~~~~~~~~~~~~~~

Create specialized loggers for specific optimization domains:

.. code-block:: python

   from lumix.utils import LXModelLogger
   from typing_extensions import Self

   class LXTransportLogger(LXModelLogger):
       """Logger specialized for transportation/routing models."""

       def log_route_creation(
           self,
           origin: str,
           destination: str,
           count: int = 1
       ) -> None:
           """Log creation of transportation routes."""
           self.logger.debug(
               f"Created {count} route(s): {origin} → {destination}"
           )

       def log_vehicle_assignment(
           self,
           vehicle_id: str,
           route: str,
           capacity: float
       ) -> None:
           """Log vehicle assignment to routes."""
           self.logger.info(
               f"Assigned vehicle {vehicle_id} to {route} (capacity: {capacity})"
           )

       def log_distance_matrix(self, size: int) -> None:
           """Log distance matrix computation."""
           self.logger.info(f"Computed distance matrix ({size}×{size})")

   # Usage
   logger = LXTransportLogger(name="routing")
   logger.log_route_creation("NYC", "BOS", count=5)
   logger.log_vehicle_assignment("V001", "NYC-BOS", capacity=1000)

Custom Log Formatters
~~~~~~~~~~~~~~~~~~~~~~

Override the log format:

.. code-block:: python

   import logging
   from lumix.utils import LXModelLogger

   class LXJSONLogger(LXModelLogger):
       """Logger that outputs JSON format."""

       def __init__(self, name: str = "lumix"):
           super().__init__(name)

           # Replace handler with JSON formatter
           import json
           from datetime import datetime

           class JSONFormatter(logging.Formatter):
               def format(self, record):
                   log_data = {
                       "timestamp": datetime.now().isoformat(),
                       "level": record.levelname,
                       "message": record.getMessage(),
                       "logger": record.name
                   }
                   return json.dumps(log_data)

           self.logger.handlers.clear()
           handler = logging.StreamHandler()
           handler.setFormatter(JSONFormatter())
           self.logger.addHandler(handler)

Multi-Output Logging
~~~~~~~~~~~~~~~~~~~~~

Log to multiple destinations:

.. code-block:: python

   import logging
   from lumix.utils import LXModelLogger

   class LXMultiOutputLogger(LXModelLogger):
       """Logger that writes to console and file."""

       def __init__(self, name: str, log_file: str):
           super().__init__(name)

           # Add file handler
           file_handler = logging.FileHandler(log_file)
           file_handler.setLevel(logging.DEBUG)
           file_handler.setFormatter(logging.Formatter(
               "%(asctime)s - %(levelname)s - %(message)s"
           ))
           self.logger.addHandler(file_handler)

   # Usage
   logger = LXMultiOutputLogger("production", "model.log")
   logger.info("This goes to both console and file")

Extending ORM Integration
--------------------------

Custom ORM Protocols
~~~~~~~~~~~~~~~~~~~~

Define protocols for specialized ORM models:

.. code-block:: python

   from typing import Protocol, runtime_checkable, Any
   from datetime import datetime

   @runtime_checkable
   class LXTimestampedModel(Protocol):
       """Protocol for models with timestamps."""
       id: Any
       created_at: datetime
       updated_at: datetime

   @runtime_checkable
   class LXSoftDeletableModel(Protocol):
       """Protocol for models with soft delete."""
       id: Any
       deleted_at: Optional[datetime]
       is_deleted: bool

   # Use in type hints
   from lumix import LXVariable

   production = LXVariable[LXTimestampedModel, float]("production")

Enhanced Query Builders
~~~~~~~~~~~~~~~~~~~~~~~~

Extend LXTypedQuery with additional functionality:

.. code-block:: python

   from typing import Optional, List, Type
   from lumix.utils.orm import LXTypedQuery
   from typing_extensions import Self

   class LXEnhancedQuery(LXTypedQuery):
       """Enhanced query with additional methods."""

       def limit(self, count: int) -> Self:
           """Limit number of results."""
           self._limit = count
           return self

       def offset(self, count: int) -> Self:
           """Skip first N results."""
           self._offset = count
           return self

       def order_by(self, key_func) -> Self:
           """Order results by key function."""
           self._order_key = key_func
           return self

       def all(self) -> List:
           """Execute with limit/offset/ordering."""
           results = super().all()

           # Apply ordering
           if hasattr(self, '_order_key'):
               results.sort(key=self._order_key)

           # Apply offset
           if hasattr(self, '_offset'):
               results = results[self._offset:]

           # Apply limit
           if hasattr(self, '_limit'):
               results = results[:self._limit]

           return results

   # Usage
   products = (
       LXEnhancedQuery(session, Product)
       .filter(lambda p: p.active)
       .order_by(lambda p: p.profit)
       .limit(10)
       .all()
   )

Pagination Support
~~~~~~~~~~~~~~~~~~

Add pagination to query results:

.. code-block:: python

   from dataclasses import dataclass
   from typing import Generic, List

   @dataclass
   class Page(Generic[TModel]):
       """Paginated results."""
       items: List[TModel]
       page: int
       per_page: int
       total: int

       @property
       def has_next(self) -> bool:
           return self.page * self.per_page < self.total

       @property
       def has_prev(self) -> bool:
           return self.page > 1

   class LXPaginatedQuery(LXTypedQuery):
       """Query builder with pagination."""

       def paginate(self, page: int = 1, per_page: int = 50) -> Page:
           """Get paginated results."""
           all_results = super().all()
           total = len(all_results)

           start = (page - 1) * per_page
           end = start + per_page
           items = all_results[start:end]

           return Page(
               items=items,
               page=page,
               per_page=per_page,
               total=total
           )

   # Usage
   page1 = LXPaginatedQuery(session, Product).paginate(page=1, per_page=20)
   print(f"Showing {len(page1.items)} of {page1.total}")

Extending Rational Conversion
------------------------------

Custom Approximation Algorithms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add new rational approximation methods:

.. code-block:: python

   from lumix.utils import LXRationalConverter
   from typing import Tuple

   class LXCustomConverter(LXRationalConverter):
       """Converter with custom approximation algorithm."""

       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           # Add support for custom method
           if kwargs.get('method') == 'custom':
               self.method = 'custom'

       def to_rational(self, value: float, return_error: bool = False):
           """Override to support custom method."""
           if self.method == 'custom':
               num, den, error = self._custom_approximation(value)
               fraction = Fraction(num, den)
               return (fraction, error) if return_error else fraction
           else:
               return super().to_rational(value, return_error)

       def _custom_approximation(self, x: float) -> Tuple[int, int, float]:
           """Custom approximation algorithm."""
           # Example: Simple rounding to nearest fraction with max_denom
           from fractions import Fraction

           # Use Python's Fraction with limit_denominator
           frac = Fraction(x).limit_denominator(self.max_denominator)

           error = abs(float(frac) - x)
           return frac.numerator, frac.denominator, error

   # Usage
   converter = LXCustomConverter(max_denominator=10000, method='custom')
   frac = converter.to_rational(3.14159)

Adaptive Precision
~~~~~~~~~~~~~~~~~~

Automatically adjust precision based on error threshold:

.. code-block:: python

   from lumix.utils import LXRationalConverter
   from fractions import Fraction

   class LXAdaptiveConverter:
       """Converter that adapts precision to meet error threshold."""

       def __init__(self, target_error: float = 1e-6):
           self.target_error = target_error

       def to_rational(self, value: float) -> Fraction:
           """Convert with adaptive precision."""
           for max_denom in [100, 1000, 10000, 100000, 1000000]:
               converter = LXRationalConverter(max_denominator=max_denom)
               frac, error = converter.to_rational(value, return_error=True)

               if error <= self.target_error:
                   return frac

           # If still not met, use largest denominator
           return frac

   # Usage
   converter = LXAdaptiveConverter(target_error=1e-8)
   frac = converter.to_rational(3.14159265359)

Cached Conversion
~~~~~~~~~~~~~~~~~

Cache conversions for repeated values:

.. code-block:: python

   from functools import lru_cache
   from lumix.utils import LXRationalConverter
   from fractions import Fraction

   class LXCachedConverter:
       """Converter with caching for performance."""

       def __init__(self, max_denominator: int = 10000):
           self.converter = LXRationalConverter(max_denominator=max_denominator)

       @lru_cache(maxsize=1000)
       def to_rational(self, value: float) -> Fraction:
           """Cached conversion."""
           return self.converter.to_rational(value)

       def clear_cache(self):
           """Clear the cache."""
           self.to_rational.cache_clear()

   # Usage
   converter = LXCachedConverter()

   # First call computes
   frac1 = converter.to_rational(3.14159)

   # Second call uses cache
   frac2 = converter.to_rational(3.14159)  # Instant!

Creating New Utilities
-----------------------

Model Validator
~~~~~~~~~~~~~~~

Create a utility to validate models before solving:

.. code-block:: python

   from typing import List
   from dataclasses import dataclass
   from lumix.core import LXModel

   @dataclass
   class ValidationError:
       """Model validation error."""
       severity: str  # "error" or "warning"
       message: str
       location: str

   class LXModelValidator:
       """Validates optimization models."""

       def validate(self, model: LXModel) -> List[ValidationError]:
           """Validate model and return errors/warnings."""
           errors = []

           # Check for variables
           if not model.variables:
               errors.append(ValidationError(
                   severity="error",
                   message="Model has no variables",
                   location="model.variables"
               ))

           # Check for objective
           if not model.objective_expr:
               errors.append(ValidationError(
                   severity="warning",
                   message="Model has no objective function",
                   location="model.objective"
               ))

           # Check for unbounded variables
           for var in model.variables:
               if var.lower_bound is None and var.upper_bound is None:
                   errors.append(ValidationError(
                       severity="warning",
                       message=f"Variable '{var.name}' is unbounded",
                       location=f"variables.{var.name}"
                   ))

           return errors

   # Usage
   validator = LXModelValidator()
   errors = validator.validate(model)

   for error in errors:
       print(f"{error.severity.upper()}: {error.message}")

Model Exporter
~~~~~~~~~~~~~~

Export models to different formats:

.. code-block:: python

   from lumix.core import LXModel
   import json

   class LXModelExporter:
       """Export models to various formats."""

       @staticmethod
       def to_dict(model: LXModel) -> dict:
           """Export model to dictionary."""
           return {
               "name": model.name,
               "num_variables": len(model.variables),
               "num_constraints": len(model.constraints),
               "objective_sense": model.objective_sense.value,
               "variables": [
                   {"name": v.name, "type": v.var_type.value}
                   for v in model.variables
               ],
               "constraints": [
                   {"name": c.name, "sense": c.sense.value}
                   for c in model.constraints
               ]
           }

       @staticmethod
       def to_json(model: LXModel, file_path: str):
           """Export model to JSON file."""
           data = LXModelExporter.to_dict(model)
           with open(file_path, 'w') as f:
               json.dump(data, f, indent=2)

   # Usage
   exporter = LXModelExporter()
   exporter.to_json(model, "model.json")

Best Practices
--------------

1. **Follow Naming Conventions**

   Use LX prefix for all LumiX utilities:

   .. code-block:: python

      # Good
      class LXCustomLogger(LXModelLogger):
          ...

      # Avoid
      class CustomLogger(LXModelLogger):
          ...

2. **Maintain Type Safety**

   Always include full type hints:

   .. code-block:: python

      from typing_extensions import Self

      def custom_method(self, value: float) -> Self:
          ...
          return self

3. **Document Extensions**

   Use Google-style docstrings:

   .. code-block:: python

      def custom_method(self, value: float) -> Fraction:
          """Custom rational approximation.

          Args:
              value: Float value to approximate

          Returns:
              Rational approximation as Fraction

          Examples:
              Basic usage::

                  converter = CustomConverter()
                  frac = converter.custom_method(3.14)
          """

4. **Add Tests**

   Test all custom functionality:

   .. code-block:: python

      def test_custom_logger():
          logger = LXTransportLogger()
          logger.log_route_creation("A", "B", count=1)
          # Assert expected behavior

See Also
--------

- :doc:`utils-architecture` - Utils architecture details
- :doc:`/api/utils/index` - Utils API reference
- :doc:`/user-guide/utils/index` - Utils usage guide
