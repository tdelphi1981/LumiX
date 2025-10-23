ORM Integration Guide
=====================

This guide covers type-safe integration between LumiX and Object-Relational Mapping (ORM)
libraries like SQLAlchemy, Django ORM, and Peewee.

Overview
--------

LumiX's ORM integration utilities provide a bridge between database models and
optimization models, enabling:

- **Type-safe queries** with full IDE autocomplete
- **Structural typing** that works with any ORM
- **Seamless data flow** from database to optimization model
- **No inheritance required** - works via Protocol (PEP 544)

**Key Components:**

- :class:`~lumix.utils.orm.LXORMModel` - Protocol for ORM models
- :class:`~lumix.utils.orm.LXORMContext` - Type-safe query wrapper
- :class:`~lumix.utils.orm.LXTypedQuery` - Fluent query builder
- :class:`~lumix.utils.orm.LXNumeric` - Protocol for numeric types

Why ORM Integration?
--------------------

Traditional Approach
~~~~~~~~~~~~~~~~~~~~

Without ORM integration, building models from database data requires manual queries
and type-unsafe operations:

.. code-block:: python

   # Manual query (no type safety)
   products = session.query(Product).all()

   # No IDE autocomplete in lambda
   production = LXVariable("production").from_data(products)

   # Type errors not caught until runtime
   model.maximize(
       LXLinearExpression().add_term(production, lambda p: p.profi)  # Typo!
   )

LumiX Approach
~~~~~~~~~~~~~~

With ORM integration, you get full type safety and IDE support:

.. code-block:: python

   from lumix.utils import LXORMContext

   # Type-safe context
   ctx = LXORMContext(session)

   # IDE autocomplete for Product attributes
   products = ctx.query(Product).filter(lambda p: p.active).all()

   # Full type safety in lambdas
   production = LXVariable[Product, float]("production").from_data(products)

   # IDE catches typos
   model.maximize(
       LXLinearExpression().add_term(production, lambda p: p.profit)  # ✓
   )

Quick Start
-----------

SQLAlchemy Example
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sqlalchemy import Column, Integer, String, Float, create_engine
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import Session

   from lumix import LXModel, LXVariable, LXLinearExpression
   from lumix.utils import LXORMContext

   # Define ORM models
   Base = declarative_base()

   class Product(Base):
       __tablename__ = 'products'
       id = Column(Integer, primary_key=True)
       name = Column(String)
       profit = Column(Float)
       cost = Column(Float)
       available = Column(Integer)

   # Create session
   engine = create_engine('sqlite:///production.db')
   session = Session(engine)

   # Type-safe queries
   ctx = LXORMContext(session)
   products = ctx.query(Product).filter(lambda p: p.available > 0).all()

   # Build optimization model
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0, upper=lambda p: p.available)
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

   model = (
       LXModel("production")
       .add_variable(production)
       .maximize(
           LXLinearExpression().add_term(production, lambda p: p.profit)
       )
   )

Django ORM Example
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from django.db import models
   from lumix import LXModel, LXVariable
   from lumix.utils import LXORMContext

   # Django model (automatically satisfies LXORMModel protocol)
   class Product(models.Model):
       name = models.CharField(max_length=100)
       profit = models.FloatField()
       cost = models.FloatField()

       class Meta:
           app_label = 'production'

   # Query and optimize
   products = Product.objects.filter(profit__gt=10)

   production = (
       LXVariable[Product, float]("production")
       .from_data(list(products))  # Convert QuerySet to list
       .indexed_by(lambda p: p.id)
   )

Core Concepts
-------------

Structural Typing (Protocol)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX uses Python's Protocol (PEP 544) for structural typing. Any object with an
``id`` attribute automatically satisfies :class:`~lumix.utils.orm.LXORMModel`:

.. code-block:: python

   from dataclasses import dataclass
   from lumix.utils import LXORMModel

   # Dataclass with id - automatically satisfies protocol
   @dataclass
   class Product:
       id: int
       name: str
       profit: float

   # No inheritance needed!
   product = Product(1, "Widget", 10.5)
   assert isinstance(product, LXORMModel)  # True

Type-Safe Queries
~~~~~~~~~~~~~~~~~

:class:`~lumix.utils.orm.LXTypedQuery` provides type-safe filtering with lambdas:

.. code-block:: python

   from lumix.utils import LXORMContext

   ctx = LXORMContext(session)

   # IDE knows 'p' is a Product
   expensive_products = (
       ctx.query(Product)
       .filter(lambda p: p.profit > 100)  # ← IDE autocomplete here!
       .filter(lambda p: p.available > 0)
       .all()
   )

Generic Type Parameters
~~~~~~~~~~~~~~~~~~~~~~~

Use type parameters for full IDE support:

.. code-block:: python

   # With type parameter
   production = LXVariable[Product, float]("production")

   # IDE knows p.profit, p.cost, etc. exist
   expr.add_term(production, lambda p: p.profit)  # ← Autocomplete!

   # Without type parameter
   production = LXVariable("production")

   # IDE doesn't know what 'p' is
   expr.add_term(production, lambda p: p.profit)  # No autocomplete

Advanced Usage
--------------

Complex Filtering
~~~~~~~~~~~~~~~~~

Chain multiple filters for complex queries:

.. code-block:: python

   ctx = LXORMContext(session)

   selected_products = (
       ctx.query(Product)
       .filter(lambda p: p.category == "Electronics")
       .filter(lambda p: p.profit > 50)
       .filter(lambda p: p.in_stock)
       .all()
   )

Multi-Model Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

Build models from multiple related tables:

.. code-block:: python

   # Define related models
   class Product(Base):
       __tablename__ = 'products'
       id = Column(Integer, primary_key=True)
       profit = Column(Float)

   class Resource(Base):
       __tablename__ = 'resources'
       id = Column(Integer, primary_key=True)
       capacity = Column(Float)

   class ProductResource(Base):
       __tablename__ = 'product_resources'
       product_id = Column(Integer)
       resource_id = Column(Integer)
       usage = Column(Float)

   # Query data
   ctx = LXORMContext(session)
   products = ctx.query(Product).all()
   resources = ctx.query(Resource).all()
   usages = session.query(ProductResource).all()

   # Build usage dictionary
   usage_dict = {
       (u.product_id, u.resource_id): u.usage
       for u in usages
   }

   # Create optimization model
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

   capacity = (
       LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression().add_term(
               production,
               lambda p, r: usage_dict.get((p.id, r.id), 0)
           )
       )
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
       .indexed_by(lambda r: r.id)
   )

   model = (
       LXModel("multi_table")
       .add_variable(production)
       .add_constraint(capacity)
       .maximize(
           LXLinearExpression().add_term(production, lambda p: p.profit)
       )
   )

Eager Loading
~~~~~~~~~~~~~

Use ORM eager loading to avoid N+1 queries:

.. code-block:: python

   from sqlalchemy.orm import joinedload

   # SQLAlchemy eager loading
   products = (
       session.query(Product)
       .options(joinedload(Product.category))
       .all()
   )

   # Now can access category without additional queries
   production = LXVariable[Product, float]("production").from_data(products)

Dynamic Model Building
~~~~~~~~~~~~~~~~~~~~~~

Build models dynamically based on database state:

.. code-block:: python

   def build_production_model(session, scenario: str):
       ctx = LXORMContext(session)

       # Query data based on scenario
       if scenario == "normal":
           products = ctx.query(Product).all()
       elif scenario == "high_demand":
           products = ctx.query(Product).filter(lambda p: p.high_demand).all()
       elif scenario == "low_cost":
           products = ctx.query(Product).filter(lambda p: p.cost < 10).all()

       # Build model from filtered data
       production = (
           LXVariable[Product, float]("production")
           .from_data(products)
           .indexed_by(lambda p: p.id)
       )

       model = (
           LXModel(f"production_{scenario}")
           .add_variable(production)
           .maximize(
               LXLinearExpression().add_term(production, lambda p: p.profit)
           )
       )

       return model

Integration Patterns
--------------------

Repository Pattern
~~~~~~~~~~~~~~~~~~

Encapsulate data access in repositories:

.. code-block:: python

   from typing import List
   from lumix.utils import LXORMContext

   class ProductRepository:
       def __init__(self, session):
           self.ctx = LXORMContext(session)

       def get_active_products(self) -> List[Product]:
           return self.ctx.query(Product).filter(lambda p: p.active).all()

       def get_profitable_products(self, min_profit: float) -> List[Product]:
           return (
               self.ctx.query(Product)
               .filter(lambda p: p.profit >= min_profit)
               .all()
           )

   # Usage
   repo = ProductRepository(session)
   products = repo.get_profitable_products(min_profit=50)

   production = LXVariable[Product, float]("production").from_data(products)

Service Layer
~~~~~~~~~~~~~

Separate business logic from data access:

.. code-block:: python

   class OptimizationService:
       def __init__(self, session):
           self.session = session
           self.ctx = LXORMContext(session)

       def optimize_production(self, scenario: str):
           # Fetch data
           products = self._get_products(scenario)
           resources = self._get_resources()

           # Build model
           model = self._build_model(products, resources)

           # Solve
           optimizer = LXOptimizer().use_solver("gurobi")
           solution = optimizer.solve(model)

           # Save results
           self._save_solution(solution, products)

           return solution

       def _get_products(self, scenario: str):
           # Data access logic
           return self.ctx.query(Product).all()

       def _build_model(self, products, resources):
           # Model building logic
           pass

       def _save_solution(self, solution, products):
           # Persist results back to database
           pass

Best Practices
--------------

1. **Filter at Database Level**

   Apply ORM-specific filters before using LXTypedQuery:

   .. code-block:: python

      # Good: Filter at database level
      products = session.query(Product).filter(Product.active == True).all()
      ctx_products = LXORMContext(session).query(Product).all()

      # Avoid: Fetching all then filtering in Python
      all_products = session.query(Product).all()
      active = [p for p in all_products if p.active]

2. **Use Type Parameters**

   Always specify type parameters for IDE support:

   .. code-block:: python

      # Good
      production = LXVariable[Product, float]("production")

      # Avoid
      production = LXVariable("production")

3. **Manage Sessions Properly**

   Use context managers for session handling:

   .. code-block:: python

      from contextlib import contextmanager

      @contextmanager
      def get_session():
          session = Session()
          try:
              yield session
              session.commit()
          except:
              session.rollback()
              raise
          finally:
              session.close()

      # Usage
      with get_session() as session:
          ctx = LXORMContext(session)
          products = ctx.query(Product).all()

4. **Cache Query Results**

   For repeated model builds, cache database queries:

   .. code-block:: python

      class CachedProductRepository:
          def __init__(self, session):
              self.ctx = LXORMContext(session)
              self._cache = {}

          def get_products(self, use_cache=True):
              if use_cache and 'products' in self._cache:
                  return self._cache['products']

              products = self.ctx.query(Product).all()
              self._cache['products'] = products
              return products

Performance Considerations
--------------------------

Query Optimization
~~~~~~~~~~~~~~~~~~

- LXTypedQuery filters in Python, not at database level
- For large datasets, use ORM filters first
- Use database indexes for frequently filtered columns
- Consider eager loading for related objects

Memory Management
~~~~~~~~~~~~~~~~~

- Fetch only needed data
- Use pagination for very large result sets
- Clear session periodically for long-running processes

Troubleshooting
---------------

IDE Not Showing Autocomplete
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ensure type parameters are specified:

.. code-block:: python

   # This should work
   var = LXVariable[Product, float]("x")
   expr.add_term(var, lambda p: p.profit)  # ← Autocomplete works

Type Checker Errors
~~~~~~~~~~~~~~~~~~~

If mypy complains about Protocol compatibility, ensure your model has the required
attributes:

.. code-block:: python

   # Model must have 'id' attribute
   class Product(Base):
       id = Column(Integer, primary_key=True)  # Required
       name = Column(String)

See Also
--------

- :class:`~lumix.utils.orm.LXORMModel` - ORM model protocol
- :class:`~lumix.utils.orm.LXORMContext` - Type-safe query context
- :class:`~lumix.utils.orm.LXTypedQuery` - Query builder
- :doc:`/api/utils/index` - Utils API reference
- SQLAlchemy: https://www.sqlalchemy.org/
- Django ORM: https://docs.djangoproject.com/en/stable/topics/db/
