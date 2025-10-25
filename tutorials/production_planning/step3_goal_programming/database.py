"""Database models using SQLAlchemy ORM for production planning with goal programming.

This module extends Step 2's ORM models with customer order support for goal programming.
Instead of raw SQL queries, we use SQLAlchemy's ORM for type-safe database operations
and seamless integration with LumiX's goal programming features.

Key Features:
    - SQLAlchemy declarative models with type safety
    - Customer tiers for priority calculation (GOLD, SILVER, BRONZE)
    - Customer orders as soft constraints (goals)
    - Automatic table creation from models
    - ORM-based CRUD operations
    - Integration with LumiX via `from_model()`
    - Session management for database transactions

Models (from Step 2):
    - Product: Manufactured items with profit and demand info
    - Machine: Production equipment with capacity
    - RawMaterial: Materials consumed during production
    - ProductionRecipe: Machine hours required per product
    - MaterialRequirement: Material consumption per product
    - ProductionSchedule: Optimized production quantities (solutions)
    - ResourceUtilization: Resource usage summary

New Models (Step 3):
    - Customer: Customer information with tier-based priority
    - CustomerOrder: Production targets from customers (soft goals)

Example:
    >>> from database import init_database, get_session
    >>> from database import Customer, CustomerOrder
    >>>
    >>> engine = init_database("sqlite:///production.db")
    >>> session = get_session(engine)
    >>>
    >>> # Add customer with tier using ORM
    >>> customer = Customer(id=1, name="Acme Corp", tier="GOLD", priority_level=1)
    >>> session.add(customer)
    >>> session.commit()
    >>>
    >>> # Add order using ORM
    >>> order = CustomerOrder(
    ...     id=1, customer_id=1, product_id=1,
    ...     target_quantity=50.0, due_week=1, priority=1
    ... )
    >>> session.add(order)
    >>> session.commit()
    >>>
    >>> # Query using ORM
    >>> customers = session.query(Customer).all()
    >>> orders = session.query(CustomerOrder).filter_by(customer_id=1).all()
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
# Product and Resource Models (from Step 2)
# ============================================================================

class Product(Base):
    """Product ORM model.

    Attributes:
        id: Primary key
        name: Product name
        profit_per_unit: Profit earned per unit produced
        min_demand: Minimum production quantity
        max_demand: Maximum production quantity
    """
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    profit_per_unit = Column(Float, nullable=False)
    min_demand = Column(Float, nullable=False, default=0.0)
    max_demand = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', profit=${self.profit_per_unit})>"


class Machine(Base):
    """Machine ORM model.

    Attributes:
        id: Primary key
        name: Machine name
        available_hours: Maximum hours available per week
    """
    __tablename__ = 'machines'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    available_hours = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Machine(id={self.id}, name='{self.name}', hours={self.available_hours})>"


class RawMaterial(Base):
    """Raw Material ORM model.

    Attributes:
        id: Primary key
        name: Material name
        available_quantity: Total quantity available
        cost_per_unit: Cost per unit of material
    """
    __tablename__ = 'raw_materials'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    available_quantity = Column(Float, nullable=False)
    cost_per_unit = Column(Float, nullable=False)

    def __repr__(self):
        return f"<RawMaterial(id={self.id}, name='{self.name}', available={self.available_quantity})>"


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
# Customer and Order Models (NEW in Step 3)
# ============================================================================

class Customer(Base):
    """Customer ORM model with tier-based priority (NEW in Step 3).

    Stores customer information including tier level which determines
    the priority of their orders in goal programming.

    Tier Levels (LumiX uses standard GP convention: lower number = higher priority):
        - GOLD: Highest priority (priority_level=1)
        - SILVER: Medium priority (priority_level=2)
        - BRONZE: Lowest priority (priority_level=3)

    Attributes:
        id: Primary key
        name: Customer name
        tier: Customer tier ('GOLD', 'SILVER', 'BRONZE')
        priority_level: Numeric priority (1=highest, 3=lowest)

    Example:
        >>> customer = Customer(
        ...     id=1, name="Acme Corp",
        ...     tier="GOLD", priority_level=1
        ... )
        >>> session.add(customer)
        >>> session.commit()
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
    """Customer Order ORM model for goal programming (NEW in Step 3).

    Stores customer orders that become soft constraints (goals) in the optimization.
    Orders have priorities based on customer tier, so high-tier customer orders
    are given higher importance.

    Note: LumiX uses standard GP convention - LOWER priority numbers = HIGHER importance (1 > 2 > 3).

    Attributes:
        id: Primary key
        customer_id: Foreign key to Customer
        product_id: Foreign key to Product
        target_quantity: Desired production quantity (soft goal)
        due_week: Week number when order is due
        priority: Priority level inherited from customer tier (1=highest, 3=lowest)

    Example:
        >>> order = CustomerOrder(
        ...     id=1, customer_id=1, product_id=1,
        ...     target_quantity=50.0, due_week=1, priority=1
        ... )
        >>> session.add(order)
        >>> session.commit()
    """
    __tablename__ = 'customer_orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    target_quantity = Column(Float, nullable=False)
    due_week = Column(Integer, nullable=False)
    priority = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 3", name='check_priority'),
        CheckConstraint("due_week >= 1", name='check_due_week'),
    )

    def __repr__(self):
        return f"<CustomerOrder(id={self.id}, customer_id={self.customer_id}, product_id={self.product_id}, qty={self.target_quantity}, priority={self.priority})>"


# ============================================================================
# Solution Models (from Step 2)
# ============================================================================

class ProductionSchedule(Base):
    """Production Schedule ORM model (optimization solution).

    Stores optimized production quantities for each product.

    Attributes:
        id: Primary key
        product_id: Foreign key to Product
        quantity: Optimized production quantity
        profit_contribution: Total profit from this product
    """
    __tablename__ = 'production_schedules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    profit_contribution = Column(Float, nullable=False)

    def __repr__(self):
        return f"<ProductionSchedule(product_id={self.product_id}, quantity={self.quantity}, profit=${self.profit_contribution})>"


class ResourceUtilization(Base):
    """Resource Utilization ORM model (solution analysis).

    Stores resource usage summary for machines and materials.

    Attributes:
        id: Primary key
        resource_type: 'machine' or 'material'
        resource_id: ID of the machine or material
        resource_name: Name of the resource
        used: Amount of resource used
        available: Total amount available
        utilization_pct: Percentage utilization
    """
    __tablename__ = 'resource_utilization'

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    resource_name = Column(String, nullable=False)
    used = Column(Float, nullable=False)
    available = Column(Float, nullable=False)
    utilization_pct = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("resource_type IN ('machine', 'material')", name='check_resource_type'),
    )

    def __repr__(self):
        return f"<ResourceUtilization({self.resource_type}: {self.resource_name}, {self.utilization_pct:.1f}%)>"


# ============================================================================
# Database Initialization and Session Management
# ============================================================================

def init_database(database_url: str = "sqlite:///production.db"):
    """Initialize database and create all tables.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy Engine instance

    Example:
        >>> engine = init_database("sqlite:///production.db")
        >>> # All tables are now created
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

    Example:
        >>> engine = init_database()
        >>> session = get_session(engine)
        >>> products = session.query(Product).all()
        >>> session.close()
    """
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def clear_all_data(session: Session):
    """Clear all data from all tables.

    Useful for resetting the database before inserting new sample data.

    Args:
        session: SQLAlchemy Session

    Example:
        >>> clear_all_data(session)
        >>> session.commit()
    """
    session.query(ResourceUtilization).delete()
    session.query(ProductionSchedule).delete()
    session.query(CustomerOrder).delete()  # NEW in Step 3
    session.query(Customer).delete()  # NEW in Step 3
    session.query(MaterialRequirement).delete()
    session.query(ProductionRecipe).delete()
    session.query(RawMaterial).delete()
    session.query(Machine).delete()
    session.query(Product).delete()
    session.commit()


# ============================================================================
# Helper Functions (from Step 2)
# ============================================================================

def get_machine_hours_required(session: Session, product_id: int, machine_id: int) -> float:
    """Get machine hours required for a product.

    Args:
        session: SQLAlchemy Session
        product_id: Product ID
        machine_id: Machine ID

    Returns:
        Hours required, or 0.0 if no recipe exists

    Example:
        >>> hours = get_machine_hours_required(session, product_id=1, machine_id=2)
    """
    recipe = session.query(ProductionRecipe).filter_by(
        product_id=product_id,
        machine_id=machine_id
    ).first()
    return recipe.hours_required if recipe else 0.0


def get_material_required(session: Session, product_id: int, material_id: int) -> float:
    """Get material quantity required for a product.

    Args:
        session: SQLAlchemy Session
        product_id: Product ID
        material_id: Material ID

    Returns:
        Quantity required, or 0.0 if no requirement exists

    Example:
        >>> qty = get_material_required(session, product_id=1, material_id=3)
    """
    req = session.query(MaterialRequirement).filter_by(
        product_id=product_id,
        material_id=material_id
    ).first()
    return req.quantity_required if req else 0.0


def create_cached_machine_hours_checker(session: Session):
    """Create a cached checker function for machine hours lookup.

    Queries all production recipes once and caches the results for
    efficient repeated lookups during constraint generation.

    Performance: Reduces from O(n) queries to O(1) lookups.

    Args:
        session: SQLAlchemy Session

    Returns:
        A checker function with signature (product_id, machine_id) -> float

    Example:
        >>> get_hours = create_cached_machine_hours_checker(session)
        >>> hours = get_hours(product_id=1, machine_id=2)  # Fast cached lookup
    """
    # Query all recipes once upfront
    recipes = session.query(ProductionRecipe).all()
    recipes_dict = {(r.product_id, r.machine_id): r.hours_required for r in recipes}

    # Return closure with cached data
    def get_hours(product_id: int, machine_id: int) -> float:
        """Get machine hours using cached data."""
        return recipes_dict.get((product_id, machine_id), 0.0)

    return get_hours


def create_cached_material_requirement_checker(session: Session):
    """Create a cached checker function for material requirement lookup.

    Queries all material requirements once and caches the results for
    efficient repeated lookups during constraint generation.

    Performance: Reduces from O(n) queries to O(1) lookups.

    Args:
        session: SQLAlchemy Session

    Returns:
        A checker function with signature (product_id, material_id) -> float

    Example:
        >>> get_material = create_cached_material_requirement_checker(session)
        >>> qty = get_material(product_id=1, material_id=3)  # Fast cached lookup
    """
    # Query all requirements once upfront
    requirements = session.query(MaterialRequirement).all()
    requirements_dict = {(r.product_id, r.material_id): r.quantity_required for r in requirements}

    # Return closure with cached data
    def get_material(product_id: int, material_id: int) -> float:
        """Get material requirement using cached data."""
        return requirements_dict.get((product_id, material_id), 0.0)

    return get_material


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
    """Get customer name by ID (NEW in Step 3)."""
    customer = session.query(Customer).filter_by(id=customer_id).first()
    return customer.name if customer else "Unknown"


# ============================================================================
# Goal Programming Helper Functions (NEW in Step 3)
# ============================================================================

def calculate_priority_from_tier(tier: str) -> int:
    """Calculate priority level from customer tier.

    LumiX uses standard goal programming convention: LOWER numbers = HIGHER priority.
    This matches the standard preemptive goal programming approach.

    Args:
        tier: Customer tier ('GOLD', 'SILVER', 'BRONZE')

    Returns:
        Priority level (1=highest, 3=lowest) - Standard GP convention

    Example:
        >>> priority = calculate_priority_from_tier("GOLD")
        >>> assert priority == 1  # Highest priority (standard convention)
    """
    tier_priority = {
        'GOLD': 1,      # Highest priority (standard GP: lower number = higher priority)
        'SILVER': 2,    # Medium priority
        'BRONZE': 3     # Lowest priority
    }
    return tier_priority.get(tier.upper(), 3)
