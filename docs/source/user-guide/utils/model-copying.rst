Model Copying and ORM Detachment
=================================

This guide explains LumiX's strategy for safely copying optimization models that use ORM (Object-Relational Mapping) data sources, enabling what-if analysis and scenario comparison.

Overview
--------

Why Model Copying is Needed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Many analysis workflows require creating modified copies of a model:

- **What-If Analysis**: Test parameter changes without affecting the original model
- **Scenario Analysis**: Compare multiple variations of the same base model
- **Sensitivity Analysis**: Explore ranges of parameter values
- **A/B Testing**: Compare different modeling approaches

The Challenge with ORM
~~~~~~~~~~~~~~~~~~~~~~~

When using database ORM frameworks (SQLAlchemy, Django), model copying faces two challenges:

1. **Session Binding**: ORM objects are bound to database sessions and cannot be pickled
2. **Lazy Loading**: Related data may not be loaded yet, causing errors after copying

**Example Problem**:

.. code-block:: python

   from copy import deepcopy

   # Build model with SQLAlchemy data
   product = session.query(Product).first()
   production = LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)
       .from_model(session)

   model.add_variable(production)

   # This will FAIL with ORM session errors!
   modified_model = deepcopy(model)  # ❌ Error: Cannot pickle session

LumiX's Solution
----------------

ORM Detachment Strategy
~~~~~~~~~~~~~~~~~~~~~~~

LumiX implements automatic ORM detachment in ``__deepcopy__`` methods:

.. mermaid::

   graph TD
       A[deepcopy model] --> B{Contains ORM objects?}
       B -->|Yes| C[Materialize lazy data]
       C --> D[Detach from session]
       D --> E[Copy as plain objects]
       B -->|No| E
       E --> F[Safe to copy!]

       style A fill:#e8f4f8
       style F fill:#e1ffe1

**Three-Step Process**:

1. **Detect ORM Objects**: Identify SQLAlchemy or Django ORM instances
2. **Materialize Data**: Force-load lazy relationships before copying
3. **Detach from Session**: Create plain Python objects with same attributes

How It Works
~~~~~~~~~~~~

The strategy is transparent - just use ``deepcopy`` normally:

.. code-block:: python

   from copy import deepcopy
   from lumix import LXModel, LXVariable

   # Build model with ORM data (session-bound objects)
   model = LXModel("production")
   production = LXVariable[Product, float]("production")
       .from_model(session)  # Uses SQLAlchemy session

   model.add_variable(production)

   # This now works! ORM objects automatically detached
   modified_model = deepcopy(model)  # ✓ Success

   # Modified model is independent (no session)
   modified_model.constraints[0].rhs_value = 1500  # Safe to modify

Supported ORM Frameworks
~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX automatically detects and handles:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Framework
     - Detection
     - Detachment Strategy
   * - **SQLAlchemy**
     - ``hasattr(obj, '_sa_instance_state')``
     - Create new instance, copy column attributes
   * - **Django ORM**
     - ``hasattr(obj, '_state') and hasattr(obj, '_meta')``
     - Copy field values to new instance
   * - **Plain Python**
     - N/A
     - Return as-is (no detachment needed)

Implementation Details
----------------------

Core Utility Functions
~~~~~~~~~~~~~~~~~~~~~~

The ``lumix.utils.copy_utils`` module provides:

detach_orm_object
^^^^^^^^^^^^^^^^^

Detach a single ORM object from its database session.

.. code-block:: python

   from lumix.utils.copy_utils import detach_orm_object

   # With SQLAlchemy
   product = session.query(Product).first()
   detached = detach_orm_object(product)
   # detached is now a plain Python object, safe to pickle

   # With plain objects (no-op)
   plain_obj = PlainProduct(id=1, name="Chair")
   result = detach_orm_object(plain_obj)
   # result is plain_obj (same object, unchanged)

**How it works for SQLAlchemy**:

1. Create new instance of same class (``cls.__new__(cls)``)
2. Initialize ``__dict__`` to make it a plain Python object
3. Copy all column attribute values as plain attributes
4. Copy loaded relationship attributes (if already loaded)
5. Return plain object with no session binding

**Signature**:

.. code-block:: python

   def detach_orm_object(obj: Any) -> Any:
       """
       Detach ORM object from session, making it safe to copy.

       Args:
           obj: Object to detach (ORM or plain object)

       Returns:
           Detached copy (ORM) or original object (plain Python)
       """

materialize_and_detach_list
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Materialize and detach a list of items that may contain ORM objects.

.. code-block:: python

   from lumix.utils.copy_utils import materialize_and_detach_list

   # List of SQLAlchemy objects
   products = session.query(Product).all()
   detached_list = materialize_and_detach_list(products, {})
   # Each item is now detached and deep copied

**Signature**:

.. code-block:: python

   def materialize_and_detach_list(
       items: Optional[List[Any]],
       memo: dict
   ) -> Optional[List[Any]]:
       """
       Materialize and detach list of items.

       Args:
           items: List of items (may contain ORM objects), or None
           memo: deepcopy memo dict for circular reference tracking

       Returns:
           New list with detached and deep-copied objects, or None
       """

copy_function_detaching_closure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy a function while detaching any ORM objects in its closure.

This is critical for lambda functions that capture ORM objects:

.. code-block:: python

   from lumix.utils.copy_utils import copy_function_detaching_closure

   # Lambda capturing ORM object
   product = session.query(Product).first()  # ORM object
   profit_func = lambda p: product.profit_per_unit * p.quantity

   # Create safe copy
   safe_func = copy_function_detaching_closure(profit_func, {})
   # safe_func uses detached copy of 'product'

**How it works**:

1. Check if function has a closure
2. Inspect each cell in the closure
3. Detect ORM objects in closure variables
4. Detach ORM objects
5. Create new function with detached closure

**Signature**:

.. code-block:: python

   def copy_function_detaching_closure(
       func: Callable,
       memo: dict
   ) -> Callable:
       """
       Copy function while detaching ORM objects in closure.

       Args:
           func: Function to copy (may have ORM objects in closure)
           memo: deepcopy memo dict for circular reference tracking

       Returns:
           New function with ORM objects detached from sessions
       """

Integration in Core Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX integrates ORM detachment into ``__deepcopy__`` methods of core classes:

LXModel.__deepcopy__
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from lumix.core.model import LXModel

   class LXModel:
       def __deepcopy__(self, memo):
           """Custom deepcopy that detaches ORM sessions."""
           # ... create new instance ...

           # Deep copy all variables (calls LXVariable.__deepcopy__)
           result.variables = [deepcopy(var, memo) for var in self.variables]

           # Deep copy all constraints (calls LXConstraint.__deepcopy__)
           result.constraints = [deepcopy(c, memo) for c in self.constraints]

           # Deep copy objective expression
           result.objective_expr = deepcopy(self.objective_expr, memo)

           return result

LXVariable.__deepcopy__
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from lumix.core.variables import LXVariable

   class LXVariable:
       def __deepcopy__(self, memo):
           """Custom deepcopy that detaches ORM and handles closures."""
           from ..utils.copy_utils import (
               materialize_and_detach_list,
               copy_function_detaching_closure
           )

           # ... create new instance ...

           # Copy callable attributes (may have closures with ORM objects)
           result.index_func = copy_function_detaching_closure(
               self.index_func, memo
           ) if self.index_func is not None else None

           result.cost_func = copy_function_detaching_closure(
               self.cost_func, memo
           ) if self.cost_func is not None else None

           # Handle data sources
           if self._session is not None:
               # Materialize ORM data before copying
               instances = self.get_instances()
               result._data = materialize_and_detach_list(instances, memo)
               result._session = None  # Clear session reference
           elif self._data is not None:
               # Already have data - just detach and copy
               result._data = materialize_and_detach_list(self._data, memo)
               result._session = None

           return result

LXConstraint.__deepcopy__
^^^^^^^^^^^^^^^^^^^^^^^^^

Similar strategy for constraints:

.. code-block:: python

   from lumix.core.constraints import LXConstraint

   class LXConstraint:
       def __deepcopy__(self, memo):
           """Custom deepcopy that detaches ORM in expressions."""
           # ... create new instance ...

           # Deep copy expression (handles ORM in coefficients)
           result.expr = deepcopy(self.expr, memo) if self.expr else None

           return result

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

Simple model copying:

.. code-block:: python

   from copy import deepcopy
   from lumix import LXModel, LXVariable, LXOptimizer

   # Build model with ORM data
   session = get_session()
   model = LXModel("production")

   production = LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_model(session)

   model.add_variable(production)

   # Copy model (ORM automatically detached)
   modified_model = deepcopy(model)

   # Safe to modify
   modified_model.constraints[0].rhs_value *= 1.5

   # Solve both
   optimizer = LXOptimizer()
   original_solution = optimizer.solve(model)
   modified_solution = optimizer.solve(modified_model)

What-If Analysis
~~~~~~~~~~~~~~~~

Using model copying for what-if analysis:

.. code-block:: python

   from copy import deepcopy
   from lumix import LXWhatIfAnalyzer

   # LXWhatIfAnalyzer uses deepcopy internally
   analyzer = LXWhatIfAnalyzer(model, optimizer)

   # Each what-if creates a modified copy
   result = analyzer.increase_constraint_rhs("capacity", by=100)

   # Behind the scenes:
   # 1. deepcopy(model) - uses ORM detachment
   # 2. Modify copied model
   # 3. Solve modified model
   # 4. Compare results

Scenario Analysis
~~~~~~~~~~~~~~~~~

Multiple model copies for scenarios:

.. code-block:: python

   from copy import deepcopy

   scenarios = {}

   # Optimistic scenario
   optimistic = deepcopy(model)
   optimistic.get_constraint("demand").rhs_value *= 1.2
   scenarios["optimistic"] = optimizer.solve(optimistic)

   # Baseline scenario
   scenarios["baseline"] = optimizer.solve(model)

   # Pessimistic scenario
   pessimistic = deepcopy(model)
   pessimistic.get_constraint("demand").rhs_value *= 0.8
   scenarios["pessimistic"] = optimizer.solve(pessimistic)

   # Compare
   for name, solution in scenarios.items():
       print(f"{name}: ${solution.objective_value:,.2f}")

Manual ORM Detachment
~~~~~~~~~~~~~~~~~~~~~

If you need to manually detach objects:

.. code-block:: python

   from lumix.utils.copy_utils import detach_orm_object

   # Detach single object
   product = session.query(Product).first()
   detached_product = detach_orm_object(product)

   # Now safe to use outside session
   session.close()
   print(detached_product.name)  # ✓ Works

Lambda with ORM in Closure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Handling lambdas that capture ORM objects:

.. code-block:: python

   from copy import deepcopy

   # Lambda captures ORM object
   product = session.query(Product).first()  # Session-bound

   production = LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data([product])

   # Add coefficient function that captures 'product'
   expr = LXLinearExpression()
   expr.add_term(production, lambda p: product.profit_per_unit)  # Captures 'product'

   # Deep copy handles this automatically!
   expr_copy = deepcopy(expr)  # ✓ Works - 'product' detached in closure

Advanced Topics
---------------

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Materialization Cost**: Lazy-loaded relationships are materialized during detachment, which can be expensive for large datasets.

**Optimization Strategies**:

1. **Eager Loading**: Use ``.options(joinedload(...))`` in queries
2. **Limit Data**: Only query needed columns
3. **Cache Results**: Reuse detached objects when possible

.. code-block:: python

   from sqlalchemy.orm import joinedload

   # Eager load relationships
   products = session.query(Product).options(
       joinedload(Product.materials),
       joinedload(Product.machine_requirements)
   ).all()

   # Now all data is loaded, detachment is faster
   production = LXVariable[Product, float]("production")
       .from_data(products)

   model_copy = deepcopy(model)  # Faster with eager loading

Circular References
~~~~~~~~~~~~~~~~~~~

The ``memo`` dict in ``deepcopy`` handles circular references:

.. code-block:: python

   # Circular reference example
   class Node:
       def __init__(self, value):
           self.value = value
           self.next = None

   # Create cycle
   node1 = Node(1)
   node2 = Node(2)
   node1.next = node2
   node2.next = node1  # Circular!

   # deepcopy handles this with memo dict
   node1_copy = deepcopy(node1)  # ✓ Works

LumiX uses the same ``memo`` dict throughout the copy process.

Pickle Support
~~~~~~~~~~~~~~

In addition to ``__deepcopy__``, LumiX implements ``__getstate__`` and ``__setstate__`` for pickle protocol:

.. code-block:: python

   import pickle

   # Build model with ORM data
   model = build_production_model(session)

   # Pickle (uses __getstate__ for ORM detachment)
   pickled = pickle.dumps(model)

   # Unpickle (uses __setstate__ for restoration)
   restored_model = pickle.loads(pickled)

   # Model works without session
   solution = optimizer.solve(restored_model)

Troubleshooting
---------------

Session Errors After Copying
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: ``DetachedInstanceError`` or ``Session is closed`` errors after copying

**Cause**: Object not properly detached from session

**Solution**: Ensure you're using ``deepcopy``, not ``copy``

.. code-block:: python

   from copy import copy, deepcopy

   # Bad - shallow copy doesn't detach
   bad_model = copy(model)  # ❌

   # Good - deep copy detaches
   good_model = deepcopy(model)  # ✓

Missing Data After Copying
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: Copied model has ``None`` or empty lists for ORM data

**Cause**: Lazy-loaded relationships not materialized before copying

**Solution**: Eager load relationships or access them before copying

.. code-block:: python

   from sqlalchemy.orm import joinedload

   # Option 1: Eager loading
   products = session.query(Product).options(
       joinedload(Product.materials)
   ).all()

   # Option 2: Touch lazy attributes before copying
   for product in products:
       _ = product.materials  # Force load
       _ = product.machine_requirements  # Force load

   # Now copy will include all data
   model_copy = deepcopy(model)

Lambda Closure Issues
~~~~~~~~~~~~~~~~~~~~~

**Symptom**: ``PicklingError`` mentioning lambda or closure

**Cause**: Lambda closure contains un-picklable objects

**Solution**: Use ``copy_function_detaching_closure`` or avoid capturing complex objects

.. code-block:: python

   from lumix.utils.copy_utils import copy_function_detaching_closure

   # Problem: Lambda captures unpicklable object
   session_obj = session  # Session cannot be pickled
   bad_func = lambda p: session_obj.query(...)  # ❌

   # Solution: Don't capture session in lambda
   good_func = lambda p: p.profit_per_unit  # ✓

Best Practices
--------------

1. **Use Eager Loading**

   Load all needed data before copying to avoid lazy-loading errors.

2. **Close Sessions Before Copying**

   Detachment makes session unnecessary - close it for clarity.

   .. code-block:: python

      # Build model
      model = build_model(session)

      # Close session (model now uses detached data)
      session.close()

      # Safe to copy
      model_copy = deepcopy(model)

3. **Avoid Complex Closures**

   Keep lambda functions simple to avoid pickling issues.

   .. code-block:: python

      # Bad: Complex closure
      def make_cost_func(session, product_id):
          product = session.query(Product).get(product_id)
          return lambda p: product.cost * p.quantity  # ❌

      # Good: Simple lambda
      def make_cost_func(product):
          cost = product.cost  # Capture value, not object
          return lambda p: cost * p.quantity  # ✓

4. **Test Copying Early**

   Verify copying works before building complex models.

   .. code-block:: python

      # Build minimal model
      model = LXModel("test")
      # ... add variables ...

      # Test copying
      try:
          model_copy = deepcopy(model)
          print("✓ Copying works!")
      except Exception as e:
          print(f"❌ Copy failed: {e}")

5. **Use Type Hints**

   Help IDE and type checkers understand ORM types.

   .. code-block:: python

      from typing import List
      from sqlalchemy.orm import Session

      def build_model(session: Session) -> LXModel:
          products: List[Product] = session.query(Product).all()
          # Type checker knows products is List[Product]

See Also
--------

- :doc:`/user-guide/analysis/whatif` - What-if analysis using model copying
- :doc:`/user-guide/analysis/scenario` - Scenario analysis
- :doc:`orm-integration` - ORM integration overview
- :doc:`/tutorials/production_planning/step7_whatif` - Tutorial using ORM copying

API Reference
~~~~~~~~~~~~~

For detailed API documentation of the ``copy_utils`` module functions, see the source code docstrings:

- ``lumix.utils.copy_utils.detach_orm_object``
- ``lumix.utils.copy_utils.materialize_and_detach_list``
- ``lumix.utils.copy_utils.copy_function_detaching_closure``

References
----------

- **SQLAlchemy Session**: https://docs.sqlalchemy.org/en/latest/orm/session.html
- **Django ORM**: https://docs.djangoproject.com/en/stable/topics/db/queries/
- **Python deepcopy**: https://docs.python.org/3/library/copy.html
