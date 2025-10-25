"""Database models using SQLAlchemy ORM for large-scale multi-period production planning.

This module extends Step 3 by adding multi-period planning capabilities with setup costs,
production batches, and inventory management. It demonstrates LumiX's ability to handle
realistic large-scale problems efficiently.

Key Features:
    - SQLAlchemy declarative models with type safety
    - Multi-period planning (4-week planning horizon)
    - Production batches with minimum batch sizes
    - Setup costs for production runs
    - Inventory tracking between periods
    - Scaled-up problem (3x products, machines, materials)
    - Customer orders with tier-based priority
    - Automatic table creation from models
    - ORM-based CRUD operations
    - Integration with LumiX
    - Session management for database transactions

Models (from Step 3):
    - Product: Manufactured items with profit and demand info
    - Machine: Production equipment with capacity
    - RawMaterial: Materials consumed during production
    - ProductionRecipe: Machine hours required per product
    - MaterialRequirement: Material consumption per product
    - Customer: Customer information with tier-based priority
    - CustomerOrder: Production targets from customers (soft goals)

New Models (Step 4):
    - Period: Planning periods (weeks)
    - ProductionBatch: Minimum batch sizes for products
    - SetupCost: Costs for starting production of a product
    - Inventory: Inventory levels between periods
    - ProductionSchedulePeriod: Production quantities by period

Scale:
    - Products: 9 (3x Step 3)
    - Machines: 6 (3x Step 3)
    - Materials: 9 (3x Step 3)
    - Periods: 4 weeks
    - Variables: ~1,600 (vs ~10 in Step 3)

Example:
    >>> from database import init_database, get_session
    >>> from database import Period, ProductionBatch, SetupCost
    >>>
    >>> engine = init_database("sqlite:///production.db")
    >>> session = get_session(engine)
    >>>
    >>> # Add period using ORM
    >>> period = Period(id=1, week_number=1, name="Week 1")
    >>> session.add(period)
    >>> session.commit()
    >>>
    >>> # Add batch constraint
    >>> batch = ProductionBatch(product_id=1, min_batch_size=10.0)
    >>> session.add(batch)
    >>> session.commit()
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    CheckConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


# ============================================================================
# Product and Resource Models (from Step 3, scaled 3x)
# ============================================================================

class Product(Base):
    """Product ORM model.

    Attributes:
        id: Primary key
        name: Product name
        profit_per_unit: Profit earned per unit produced
        min_demand: Minimum production quantity
        max_demand: Maximum production quantity per period
        holding_cost_per_unit: Cost to hold one unit in inventory per period
    """
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    profit_per_unit = Column(Float, nullable=False)
    min_demand = Column(Float, nullable=False, default=0.0)
    max_demand = Column(Float, nullable=False)
    holding_cost_per_unit = Column(Float, nullable=False, default=1.0)

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', profit=${self.profit_per_unit})>"


class Machine(Base):
    """Machine ORM model.

    Attributes:
        id: Primary key
        name: Machine name
        available_hours: Maximum hours available per week
        hourly_cost: Operating cost per hour
    """
    __tablename__ = 'machines'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    available_hours = Column(Float, nullable=False)
    hourly_cost = Column(Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<Machine(id={self.id}, name='{self.name}', hours={self.available_hours})>"


class RawMaterial(Base):
    """Raw Material ORM model.

    Attributes:
        id: Primary key
        name: Material name
        available_quantity_per_period: Quantity available each period
        cost_per_unit: Cost per unit of material
    """
    __tablename__ = 'raw_materials'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    available_quantity_per_period = Column(Float, nullable=False)
    cost_per_unit = Column(Float, nullable=False)

    def __repr__(self):
        return f"<RawMaterial(id={self.id}, name='{self.name}', available={self.available_quantity_per_period})>"


class ProductionRecipe(Base):
    """Production Recipe ORM model (relationship table).

    Maps products to machines with required hours.

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        machine_id: Foreign key to Machine
        hours_required: Machine hours needed per unit
    """
    __tablename__ = 'production_recipes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    hours_required = Column(Float, nullable=False)

    def __repr__(self):
        return f"<ProductionRecipe(product_id={self.product_id}, machine_id={self.machine_id}, hours={self.hours_required})>"


class MaterialRequirement(Base):
    """Material Requirement ORM model (relationship table).

    Maps products to raw materials with required quantities.

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        material_id: Foreign key to RawMaterial
        quantity_required: Material units needed per product unit
    """
    __tablename__ = 'material_requirements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('raw_materials.id'), nullable=False)
    quantity_required = Column(Float, nullable=False)

    def __repr__(self):
        return f"<MaterialRequirement(product_id={self.product_id}, material_id={self.material_id}, qty={self.quantity_required})>"


# ============================================================================
# Customer and Order Models (from Step 3)
# ============================================================================

class Customer(Base):
    """Customer ORM model with tier-based priority.

    Attributes:
        id: Primary key
        name: Customer name
        tier: Customer tier ('GOLD', 'SILVER', 'BRONZE')
        priority_level: Numeric priority (1=highest, 3=lowest)
    """
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    tier = Column(String, nullable=False)
    priority_level = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("tier IN ('GOLD', 'SILVER', 'BRONZE')", name='check_tier'),
        CheckConstraint("priority_level BETWEEN 1 AND 3", name='check_priority_level'),
    )

    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', tier='{self.tier}', priority={self.priority_level})>"


class CustomerOrder(Base):
    """Customer Order ORM model for goal programming.

    Attributes:
        id: Primary key
        customer_id: Foreign key to Customer
        product_id: Foreign key to Product
        period_id: Foreign key to Period (delivery period)
        target_quantity: Desired production quantity (soft goal)
        priority: Priority level inherited from customer tier
    """
    __tablename__ = 'customer_orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    period_id = Column(Integer, ForeignKey('periods.id'), nullable=False)
    target_quantity = Column(Float, nullable=False)
    priority = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 3", name='check_priority'),
    )

    def __repr__(self):
        return f"<CustomerOrder(id={self.id}, customer_id={self.customer_id}, product_id={self.product_id}, period={self.period_id}, qty={self.target_quantity})>"


# ============================================================================
# Multi-Period Models (NEW in Step 4)
# ============================================================================

class Period(Base):
    """Period ORM model for multi-period planning (NEW in Step 4).

    Represents a planning period (typically one week).

    Attributes:
        id: Primary key
        week_number: Week number (1, 2, 3, 4)
        name: Human-readable period name
    """
    __tablename__ = 'periods'

    id = Column(Integer, primary_key=True)
    week_number = Column(Integer, nullable=False, unique=True)
    name = Column(String, nullable=False)

    def __repr__(self):
        return f"<Period(id={self.id}, week={self.week_number}, name='{self.name}')>"


class ProductionBatch(Base):
    """Production Batch ORM model (NEW in Step 4).

    Defines minimum batch sizes for production runs. If a product is produced
    in a period, at least min_batch_size units must be produced.

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        min_batch_size: Minimum units per production run
    """
    __tablename__ = 'production_batches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, unique=True)
    min_batch_size = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("min_batch_size > 0", name='check_min_batch_size'),
    )

    def __repr__(self):
        return f"<ProductionBatch(product_id={self.product_id}, min_batch={self.min_batch_size})>"


class SetupCost(Base):
    """Setup Cost ORM model (NEW in Step 4).

    Represents fixed costs incurred when starting production of a product
    in a period (setup time, changeover costs, etc.).

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        machine_id: Foreign key to Machine
        cost: Fixed cost for setup
        setup_hours: Hours required for setup
    """
    __tablename__ = 'setup_costs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    cost = Column(Float, nullable=False)
    setup_hours = Column(Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<SetupCost(product_id={self.product_id}, machine_id={self.machine_id}, cost=${self.cost})>"


class Inventory(Base):
    """Inventory ORM model (NEW in Step 4).

    Tracks inventory levels of products at the end of each period.

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        period_id: Foreign key to Period
        quantity: Units in inventory at end of period
    """
    __tablename__ = 'inventory'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    period_id = Column(Integer, ForeignKey('periods.id'), nullable=False)
    quantity = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Inventory(product_id={self.product_id}, period_id={self.period_id}, qty={self.quantity})>"


# ============================================================================
# Solution Models (Extended for Multi-Period)
# ============================================================================

class ProductionSchedulePeriod(Base):
    """Production Schedule by Period ORM model (optimization solution).

    Stores optimized production quantities for each product in each period.

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        period_id: Foreign key to Period
        quantity: Optimized production quantity
        profit_contribution: Total profit from this product in this period
    """
    __tablename__ = 'production_schedules_period'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    period_id = Column(Integer, ForeignKey('periods.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    profit_contribution = Column(Float, nullable=False)

    def __repr__(self):
        return f"<ProductionSchedulePeriod(product_id={self.product_id}, period_id={self.period_id}, quantity={self.quantity})>"


class ResourceUtilizationPeriod(Base):
    """Resource Utilization by Period ORM model (solution analysis).

    Stores resource usage summary for machines and materials in each period.

    Attributes:
        id: Primary key
        resource_type: 'machine' or 'material'
        resource_id: ID of the machine or material
        period_id: Foreign key to Period
        resource_name: Name of the resource
        used: Amount of resource used
        available: Total amount available
        utilization_pct: Percentage utilization
    """
    __tablename__ = 'resource_utilization_period'

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    period_id = Column(Integer, ForeignKey('periods.id'), nullable=False)
    resource_name = Column(String, nullable=False)
    used = Column(Float, nullable=False)
    available = Column(Float, nullable=False)
    utilization_pct = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("resource_type IN ('machine', 'material')", name='check_resource_type'),
    )

    def __repr__(self):
        return f"<ResourceUtilizationPeriod({self.resource_type}: {self.resource_name}, period={self.period_id}, {self.utilization_pct:.1f}%)>"


# ============================================================================
# Database Initialization and Session Management
# ============================================================================

def init_database(database_url: str = "sqlite:///production.db"):
    """Initialize database and create all tables.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy Engine instance
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    """Create a new database session.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        SQLAlchemy Session for database operations
    """
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def clear_all_data(session: Session):
    """Clear all data from all tables.

    Args:
        session: SQLAlchemy Session
    """
    session.query(ResourceUtilizationPeriod).delete()
    session.query(ProductionSchedulePeriod).delete()
    session.query(Inventory).delete()
    session.query(SetupCost).delete()
    session.query(ProductionBatch).delete()
    session.query(CustomerOrder).delete()
    session.query(Customer).delete()
    session.query(MaterialRequirement).delete()
    session.query(ProductionRecipe).delete()
    session.query(RawMaterial).delete()
    session.query(Machine).delete()
    session.query(Product).delete()
    session.query(Period).delete()
    session.commit()


# ============================================================================
# Helper Functions (from Step 3)
# ============================================================================

def get_machine_hours_required(session: Session, product_id: int, machine_id: int) -> float:
    """Get machine hours required for a product."""
    recipe = session.query(ProductionRecipe).filter_by(
        product_id=product_id,
        machine_id=machine_id
    ).first()
    return recipe.hours_required if recipe else 0.0


def get_material_required(session: Session, product_id: int, material_id: int) -> float:
    """Get material quantity required for a product."""
    req = session.query(MaterialRequirement).filter_by(
        product_id=product_id,
        material_id=material_id
    ).first()
    return req.quantity_required if req else 0.0


def create_cached_machine_hours_checker(session: Session):
    """Create a cached checker function for machine hours lookup.

    Performance: Reduces from O(n) queries to O(1) lookups.
    """
    recipes = session.query(ProductionRecipe).all()
    recipes_dict = {(r.product_id, r.machine_id): r.hours_required for r in recipes}

    def get_hours(product_id: int, machine_id: int) -> float:
        return recipes_dict.get((product_id, machine_id), 0.0)

    return get_hours


def create_cached_material_requirement_checker(session: Session):
    """Create a cached checker function for material requirement lookup.

    Performance: Reduces from O(n) queries to O(1) lookups.
    """
    requirements = session.query(MaterialRequirement).all()
    requirements_dict = {(r.product_id, r.material_id): r.quantity_required for r in requirements}

    def get_material(product_id: int, material_id: int) -> float:
        return requirements_dict.get((product_id, material_id), 0.0)

    return get_material


# ============================================================================
# Multi-Period Helper Functions (NEW in Step 4)
# ============================================================================

def get_batch_size(session: Session, product_id: int) -> float:
    """Get minimum batch size for a product.

    Args:
        session: SQLAlchemy Session
        product_id: Product ID

    Returns:
        Minimum batch size, or 0.0 if no batch constraint exists
    """
    batch = session.query(ProductionBatch).filter_by(product_id=product_id).first()
    return batch.min_batch_size if batch else 0.0


def get_setup_cost(session: Session, product_id: int, machine_id: int) -> tuple:
    """Get setup cost and hours for a product on a machine.

    Args:
        session: SQLAlchemy Session
        product_id: Product ID
        machine_id: Machine ID

    Returns:
        Tuple of (cost, setup_hours), or (0.0, 0.0) if no setup exists
    """
    setup = session.query(SetupCost).filter_by(
        product_id=product_id,
        machine_id=machine_id
    ).first()
    return (setup.cost, setup.setup_hours) if setup else (0.0, 0.0)


def create_cached_batch_size_checker(session: Session):
    """Create a cached checker function for batch size lookup.

    Performance: Reduces from O(n) queries to O(1) lookups.
    """
    batches = session.query(ProductionBatch).all()
    batch_dict = {b.product_id: b.min_batch_size for b in batches}

    def get_batch(product_id: int) -> float:
        return batch_dict.get(product_id, 0.0)

    return get_batch


def create_cached_setup_cost_checker(session: Session):
    """Create a cached checker function for setup cost lookup.

    Performance: Reduces from O(n) queries to O(1) lookups.
    """
    setups = session.query(SetupCost).all()
    setup_dict = {(s.product_id, s.machine_id): (s.cost, s.setup_hours) for s in setups}

    def get_setup(product_id: int, machine_id: int) -> tuple:
        return setup_dict.get((product_id, machine_id), (0.0, 0.0))

    return get_setup


# ============================================================================
# Name Lookup Helper Functions
# ============================================================================

def get_product_name(session: Session, product_id: int) -> str:
    """Get product name by ID."""
    product = session.query(Product).filter_by(id=product_id).first()
    return product.name if product else "Unknown"


def get_machine_name(session: Session, machine_id: int) -> str:
    """Get machine name by ID."""
    machine = session.query(Machine).filter_by(id=machine_id).first()
    return machine.name if machine else "Unknown"


def get_material_name(session: Session, material_id: int) -> str:
    """Get material name by ID."""
    material = session.query(RawMaterial).filter_by(id=material_id).first()
    return material.name if material else "Unknown"


def get_customer_name(session: Session, customer_id: int) -> str:
    """Get customer name by ID."""
    customer = session.query(Customer).filter_by(id=customer_id).first()
    return customer.name if customer else "Unknown"


def get_period_name(session: Session, period_id: int) -> str:
    """Get period name by ID."""
    period = session.query(Period).filter_by(id=period_id).first()
    return period.name if period else "Unknown"


# ============================================================================
# Goal Programming Helper Functions (from Step 3)
# ============================================================================

def calculate_priority_from_tier(tier: str) -> int:
    """Calculate priority level from customer tier."""
    tier_priority = {
        'GOLD': 1,
        'SILVER': 2,
        'BRONZE': 3
    }
    return tier_priority.get(tier.upper(), 3)
