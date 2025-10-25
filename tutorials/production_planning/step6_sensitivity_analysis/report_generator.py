"""Interactive HTML Report Generator for Production Planning with Sensitivity Analysis.

This module generates a modern, interactive HTML5 + CSS dashboard for visualizing
multi-period production optimization results with comprehensive sensitivity analysis.

Features (from Step 4):
    - Summary dashboard with key performance metrics
    - Multi-period production schedule with weekly breakdown
    - Resource utilization analysis (machines & materials)
    - Customer order fulfillment tracking by priority
    - Financial breakdown with cost analysis

New Features (Step 6 - Sensitivity Analysis):
    - Sensitivity analysis dashboard with key metrics
    - Shadow price analysis for all constraints
    - Bottleneck identification and ranking
    - Investment recommendations based on marginal values
    - Binding constraint visualization
    - Top N most sensitive parameters

Usage:
    >>> from report_generator import generate_html_report
    >>> generate_html_report(solution, session, analyzer, "production_sensitivity_report.html")
"""

from typing import Dict, List, Tuple, Any
from database import (
    Product,
    Period,
    Machine,
    RawMaterial,
    Customer,
    CustomerOrder,
    ProductionBatch,
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
)


def extract_production_data(solution, session) -> Dict[Tuple[int, int], float]:
    """Extract production quantities from solution."""
    production_data = {}
    for (product_id, period_id), value in solution.variables["production"].items():
        if value > 0.01:
            production_data[(product_id, period_id)] = value
    return production_data


def extract_inventory_data(solution, session) -> Dict[Tuple[int, int], float]:
    """Extract inventory levels from solution."""
    inventory_data = {}
    for (product_id, period_id), value in solution.variables["inventory"].items():
        inventory_data[(product_id, period_id)] = value
    return inventory_data


def extract_sensitivity_data(analyzer, session) -> Dict[str, Any]:
    """Extract sensitivity analysis data from analyzer.

    Args:
        analyzer: LXSensitivityAnalyzer instance
        session: SQLAlchemy Session

    Returns:
        Dictionary containing sensitivity analysis results
    """
    # Get all constraint sensitivities
    all_constraints = analyzer.analyze_all_constraints()

    # Get binding constraints
    binding_constraints = analyzer.get_binding_constraints()

    # Get bottlenecks
    bottlenecks = analyzer.identify_bottlenecks(shadow_price_threshold=0.01)

    # Get top sensitive constraints
    top_sensitive = analyzer.get_most_sensitive_constraints(top_n=10)

    # Get batch sizes for normalization
    batches = session.query(ProductionBatch).all()
    batch_size_map = {b.product_id: b.min_batch_size for b in batches}

    # Helper function to normalize shadow prices for batch constraints
    def normalize_shadow_price(constraint_name: str, shadow_price: float) -> tuple:
        """Normalize shadow price for batch constraints.

        Returns:
            (normalized_shadow_price, batch_size) or (shadow_price, None) if not a batch constraint
        """
        if constraint_name.startswith("batch_"):
            # Parse: batch_<product_id>_period_<period_id>
            parts = constraint_name.split("_")
            if len(parts) >= 2:
                try:
                    product_id = int(parts[1])
                    batch_size = batch_size_map.get(product_id)
                    if batch_size and batch_size > 0:
                        return (shadow_price / batch_size, batch_size)
                except (ValueError, IndexError):
                    pass
        return (shadow_price, None)

    # Organize by constraint type
    machine_sensitivity = {}
    material_sensitivity = {}

    machines = session.query(Machine).all()
    materials = session.query(RawMaterial).all()
    periods = session.query(Period).order_by(Period.week_number).all()

    # Extract machine constraint sensitivities
    for machine in machines:
        for period in periods:
            constraint_name = f"machine_{machine.id}_period_{period.id}"
            if constraint_name in all_constraints:
                sens = all_constraints[constraint_name]
                machine_sensitivity[(machine.id, period.id)] = {
                    "name": machine.name,
                    "period": period.name,
                    "shadow_price": sens.shadow_price or 0.0,
                    "is_binding": sens.is_binding,
                }

    # Extract material constraint sensitivities
    for material in materials:
        for period in periods:
            constraint_name = f"material_{material.id}_period_{period.id}"
            if constraint_name in all_constraints:
                sens = all_constraints[constraint_name]
                material_sensitivity[(material.id, period.id)] = {
                    "name": material.name,
                    "period": period.name,
                    "shadow_price": sens.shadow_price or 0.0,
                    "is_binding": sens.is_binding,
                }

    return {
        "all_constraints": all_constraints,
        "binding_constraints": binding_constraints,
        "bottlenecks": bottlenecks,
        "top_sensitive": top_sensitive,
        "machine_sensitivity": machine_sensitivity,
        "material_sensitivity": material_sensitivity,
        "num_binding": len(binding_constraints),
        "num_bottlenecks": len(bottlenecks),
        "batch_size_map": batch_size_map,
        "normalize_shadow_price": normalize_shadow_price,
    }


def calculate_statistics(solution, session, production_data: Dict, inventory_data: Dict) -> Dict[str, Any]:
    """Calculate summary statistics for the dashboard."""
    products = session.query(Product).all()
    periods = session.query(Period).order_by(Period.week_number).all()
    machines = session.query(Machine).all()
    materials = session.query(RawMaterial).all()
    orders = session.query(CustomerOrder).all()

    get_hours = create_cached_machine_hours_checker(session)
    get_material = create_cached_material_requirement_checker(session)

    # Calculate total profit
    total_profit = 0.0
    for (product_id, period_id), qty in production_data.items():
        product = next((p for p in products if p.id == product_id), None)
        if product:
            total_profit += qty * product.profit_per_unit

    # Calculate profit by period
    profit_by_period = {}
    for period in periods:
        period_profit = 0.0
        for (product_id, period_id), qty in production_data.items():
            if period_id == period.id:
                product = next((p for p in products if p.id == product_id), None)
                if product:
                    period_profit += qty * product.profit_per_unit
        profit_by_period[period.id] = period_profit

    # Count production runs
    production_runs = len([v for v in production_data.values() if v > 0.01])

    # Calculate machine utilization
    machine_utilization = {}
    for period in periods:
        for machine in machines:
            hours_used = 0.0
            for (product_id, period_id), qty in production_data.items():
                if period_id == period.id:
                    hours_required = get_hours(product_id, machine.id)
                    hours_used += qty * hours_required

            utilization_pct = (hours_used / machine.available_hours * 100) if machine.available_hours > 0 else 0
            machine_utilization[(machine.id, period.id)] = {
                "used": hours_used,
                "available": machine.available_hours,
                "pct": utilization_pct
            }

    # Overall machine utilization
    total_machine_hours_used = sum(v["used"] for v in machine_utilization.values())
    total_machine_hours_available = len(periods) * sum(m.available_hours for m in machines)
    overall_machine_util = (total_machine_hours_used / total_machine_hours_available * 100) if total_machine_hours_available > 0 else 0

    # Calculate material consumption
    material_consumption = {}
    for period in periods:
        for material in materials:
            used = 0.0
            for (product_id, period_id), qty in production_data.items():
                if period_id == period.id:
                    material_required = get_material(product_id, material.id)
                    used += qty * material_required

            remaining = material.available_quantity_per_period - used
            utilization_pct = (used / material.available_quantity_per_period * 100) if material.available_quantity_per_period > 0 else 0

            material_consumption[(material.id, period.id)] = {
                "used": used,
                "available": material.available_quantity_per_period,
                "remaining": remaining,
                "pct": utilization_pct
            }

    # Overall material utilization
    total_material_used = sum(v["used"] for v in material_consumption.values())
    total_material_available = len(periods) * sum(m.available_quantity_per_period for m in materials)
    overall_material_util = (total_material_used / total_material_available * 100) if total_material_available > 0 else 0

    # Calculate order fulfillment by priority
    order_fulfillment = {1: {"satisfied": 0, "total": 0},
                        2: {"satisfied": 0, "total": 0},
                        3: {"satisfied": 0, "total": 0}}

    products_dict = {p.id: p for p in products}

    for order in orders:
        order_fulfillment[order.priority]["total"] += 1

        product = products_dict.get(order.product_id)
        if product:
            actual_production = production_data.get((order.product_id, order.period_id), 0.0)
            if actual_production >= order.target_quantity - 0.01:
                order_fulfillment[order.priority]["satisfied"] += 1

    # Count unique products
    unique_products = len(set(prod_id for (prod_id, per_id) in production_data.keys()))

    return {
        "total_profit": total_profit,
        "profit_by_period": profit_by_period,
        "production_runs": production_runs,
        "unique_products": unique_products,
        "total_periods": len(periods),
        "machine_utilization": machine_utilization,
        "overall_machine_util": overall_machine_util,
        "material_consumption": material_consumption,
        "overall_material_util": overall_material_util,
        "order_fulfillment": order_fulfillment,
        "solution_status": solution.status,
    }


def generate_product_colors() -> Dict[str, str]:
    """Generate consistent color palette for products."""
    return {
        "Chair": "#3498db",
        "Table": "#27ae60",
        "Desk": "#9b59b6",
        "Sofa": "#e74c3c",
        "Bookcase": "#f39c12",
        "Cabinet": "#1abc9c",
        "Bed": "#e67e22",
        "Wardrobe": "#34495e",
        "Nightstand": "#16a085",
    }


def generate_sensitivity_dashboard_html(sensitivity_data: Dict, stats: Dict) -> str:
    """Generate HTML for sensitivity analysis dashboard.

    Args:
        sensitivity_data: Sensitivity analysis results
        stats: Statistics dictionary

    Returns:
        HTML string for sensitivity dashboard
    """
    num_binding = sensitivity_data["num_binding"]
    num_bottlenecks = sensitivity_data["num_bottlenecks"]

    # Calculate average shadow price for binding constraints
    binding_constraints = sensitivity_data["binding_constraints"]
    if binding_constraints:
        avg_shadow_price = sum(abs(sens.shadow_price or 0) for sens in binding_constraints.values()) / len(binding_constraints)
    else:
        avg_shadow_price = 0.0

    # Risk assessment
    if num_binding >= 10:
        risk_level = "HIGH"
        risk_color = "#e74c3c"
        risk_message = "Solution is highly sensitive to parameter changes. Multiple bottlenecks identified."
    elif num_binding >= 5:
        risk_level = "MODERATE"
        risk_color = "#f39c12"
        risk_message = "Several binding constraints found. Focus on top bottlenecks for capacity expansion."
    else:
        risk_level = "LOW"
        risk_color = "#27ae60"
        risk_message = "Solution is robust to parameter variations. Good capacity buffer available."

    html = f"""
    <div class="sensitivity-dashboard">
        <div class="dashboard-grid">
            <div class="stat-card sensitivity-card">
                <h3>Binding Constraints</h3>
                <div class="stat-value">{num_binding}</div>
                <div class="stat-label">At Capacity</div>
            </div>
            <div class="stat-card sensitivity-card">
                <h3>Identified Bottlenecks</h3>
                <div class="stat-value">{num_bottlenecks}</div>
                <div class="stat-label">High Priority</div>
            </div>
            <div class="stat-card sensitivity-card">
                <h3>Avg Shadow Price</h3>
                <div class="stat-value">${avg_shadow_price:.2f}</div>
                <div class="stat-label">Per Unit Value</div>
            </div>
            <div class="stat-card sensitivity-card" style="background: linear-gradient(135deg, {risk_color} 0%, {risk_color}dd 100%);">
                <h3>Sensitivity Risk</h3>
                <div class="stat-value">{risk_level}</div>
                <div class="stat-label">{risk_message}</div>
            </div>
        </div>

        <div class="dashboard-section">
            <h2>Shadow Price Interpretation</h2>
            <div class="info-box">
                <p><strong>Shadow Price:</strong> The marginal value of relaxing a constraint by one unit.</p>
                <ul>
                    <li>Positive shadow price → Constraint is binding (at capacity)</li>
                    <li>Zero shadow price → Constraint has slack (not limiting)</li>
                    <li>Higher shadow price → Higher priority for capacity expansion</li>
                </ul>
                <p><strong>Business Use:</strong> Shadow prices guide investment decisions. If a machine's shadow price is $5.00/hour,
                each additional hour of capacity increases profit by $5.00 (up to the basis change limit).</p>
            </div>
        </div>
    </div>
    """

    return html


def generate_shadow_price_analysis_html(sensitivity_data: Dict, session) -> str:
    """Generate HTML for shadow price analysis.

    Args:
        sensitivity_data: Sensitivity analysis results
        session: SQLAlchemy Session

    Returns:
        HTML string for shadow price analysis
    """
    machine_sensitivity = sensitivity_data["machine_sensitivity"]
    material_sensitivity = sensitivity_data["material_sensitivity"]

    machines = session.query(Machine).all()
    materials = session.query(RawMaterial).all()
    periods = session.query(Period).order_by(Period.week_number).all()

    html = """
    <div class="shadow-price-analysis">
        <h2>Machine Capacity Shadow Prices</h2>
        <table class="shadow-price-table">
            <thead>
                <tr>
                    <th>Machine</th>
    """

    for period in periods:
        html += f"<th>{period.name}</th>"

    html += "<th>Average</th></tr></thead><tbody>"

    for machine in sorted(machines, key=lambda m: m.name):
        html += f"<tr><td class='resource-name'><strong>{machine.name}</strong></td>"

        total_shadow = 0.0
        count = 0

        for period in periods:
            sens_data = machine_sensitivity.get((machine.id, period.id), {})
            shadow_price = sens_data.get("shadow_price", 0.0)
            is_binding = sens_data.get("is_binding", False)

            total_shadow += abs(shadow_price)
            count += 1

            # Color code by shadow price magnitude
            if abs(shadow_price) > 1.0:
                color_class = "shadow-high"
            elif abs(shadow_price) > 0.1:
                color_class = "shadow-medium"
            else:
                color_class = "shadow-low"

            binding_indicator = "🔴" if is_binding else ""

            html += f"""
            <td class='shadow-cell {color_class}'>
                <span class='shadow-value'>${shadow_price:.2f}</span> {binding_indicator}
                <div class='shadow-tooltip'>
                    Shadow Price: ${shadow_price:.4f}<br/>
                    Status: {'BINDING (at capacity)' if is_binding else 'Slack available'}<br/>
                    Impact: +${abs(shadow_price):.2f} profit per unit
                </div>
            </td>
            """

        avg_shadow = total_shadow / count if count > 0 else 0
        html += f"<td class='avg-cell'>${avg_shadow:.2f}</td>"
        html += "</tr>"

    html += "</tbody></table>"

    html += """
        <div style="margin-top: 30px;">
            <h2>Material Availability Shadow Prices</h2>
            <table class="shadow-price-table">
                <thead>
                    <tr>
                        <th>Material</th>
    """

    for period in periods:
        html += f"<th>{period.name}</th>"

    html += "<th>Average</th></tr></thead><tbody>"

    for material in sorted(materials, key=lambda m: m.name):
        html += f"<tr><td class='resource-name'><strong>{material.name}</strong></td>"

        total_shadow = 0.0
        count = 0

        for period in periods:
            sens_data = material_sensitivity.get((material.id, period.id), {})
            shadow_price = sens_data.get("shadow_price", 0.0)
            is_binding = sens_data.get("is_binding", False)

            total_shadow += abs(shadow_price)
            count += 1

            if abs(shadow_price) > 1.0:
                color_class = "shadow-high"
            elif abs(shadow_price) > 0.1:
                color_class = "shadow-medium"
            else:
                color_class = "shadow-low"

            binding_indicator = "🔴" if is_binding else ""

            html += f"""
            <td class='shadow-cell {color_class}'>
                <span class='shadow-value'>${shadow_price:.2f}</span> {binding_indicator}
                <div class='shadow-tooltip'>
                    Shadow Price: ${shadow_price:.4f}<br/>
                    Status: {'BINDING (at capacity)' if is_binding else 'Slack available'}<br/>
                    Impact: +${abs(shadow_price):.2f} profit per unit
                </div>
            </td>
            """

        avg_shadow = total_shadow / count if count > 0 else 0
        html += f"<td class='avg-cell'>${avg_shadow:.2f}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"

    html += """
        <div class="legend" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h3>Legend:</h3>
            <p>🔴 = Binding constraint (at capacity)</p>
            <p><span style="padding: 2px 8px; background: #ffe0e0; border-radius: 4px;">High</span> = Shadow price > $1.00 (high priority)</p>
            <p><span style="padding: 2px 8px; background: #fff3cd; border-radius: 4px;">Medium</span> = Shadow price $0.10-$1.00 (medium priority)</p>
            <p><span style="padding: 2px 8px; background: #e8e8e8; border-radius: 4px;">Low</span> = Shadow price < $0.10 (low priority)</p>
        </div>
    </div>
    """

    return html


def generate_bottleneck_analysis_html(sensitivity_data: Dict) -> str:
    """Generate HTML for bottleneck analysis.

    Args:
        sensitivity_data: Sensitivity analysis results

    Returns:
        HTML string for bottleneck analysis
    """
    top_sensitive = sensitivity_data["top_sensitive"]
    normalize_fn = sensitivity_data["normalize_shadow_price"]

    html = """
    <div class="bottleneck-analysis">
        <h2>Top 10 Bottlenecks (Ranked by Shadow Price)</h2>
        <div class="info-box">
            <p>Bottlenecks are binding constraints with significant shadow prices. These represent the highest-value
            opportunities for capacity expansion. Prioritize addressing these constraints to maximize profit improvement.</p>
            <p><strong>Note:</strong> Shadow prices for batch constraints are normalized by dividing by the minimum batch size
            to show the actual marginal value per constraint unit.</p>
        </div>

        <table class="bottleneck-table">
            <thead>
                <tr>
                    <th style="width: 50px;">Rank</th>
                    <th>Constraint</th>
                    <th>Shadow Price (Normalized)</th>
                    <th>Priority</th>
                    <th>Expected Impact</th>
                </tr>
            </thead>
            <tbody>
    """

    if top_sensitive:
        for i, (name, sens) in enumerate(top_sensitive, 1):
            raw_shadow_price = sens.shadow_price or 0.0

            # Normalize shadow price for batch constraints
            normalized_shadow_price, batch_size = normalize_fn(name, raw_shadow_price)
            shadow_price = normalized_shadow_price

            # Determine priority level based on normalized value
            if abs(shadow_price) > 1.0:
                priority = "HIGH"
                priority_badge = "priority-high"
            elif abs(shadow_price) > 0.1:
                priority = "MEDIUM"
                priority_badge = "priority-medium"
            else:
                priority = "LOW"
                priority_badge = "priority-low"

            # Format constraint name for display
            display_name = name.replace("_", " ").title()

            # Add batch size info if applicable
            if batch_size:
                shadow_price_display = f"${shadow_price:.2f} (÷{batch_size:.0f})"
            else:
                shadow_price_display = f"${shadow_price:.2f}"

            html += f"""
                <tr class="bottleneck-row">
                    <td class="rank-cell">#{i}</td>
                    <td class="constraint-name">{display_name}</td>
                    <td class="shadow-price-cell">{shadow_price_display}</td>
                    <td><span class="priority-badge {priority_badge}">{priority}</span></td>
                    <td class="impact-cell">+${abs(shadow_price):.2f} profit per unit relaxation</td>
                </tr>
            """
    else:
        html += """
                <tr>
                    <td colspan="5" style="text-align: center; padding: 30px;">
                        No significant bottlenecks identified. All constraints have slack capacity.
                    </td>
                </tr>
        """

    html += """
            </tbody>
        </table>

        <div class="recommendations" style="margin-top: 30px;">
            <h3>Investment Recommendations</h3>
    """

    if top_sensitive and len(top_sensitive) > 0:
        html += """
            <div class="recommendation-grid">
        """

        for i, (name, sens) in enumerate(top_sensitive[:3], 1):
            raw_shadow_price = sens.shadow_price or 0.0
            normalized_shadow_price, batch_size = normalize_fn(name, raw_shadow_price)
            shadow_price = normalized_shadow_price
            display_name = name.replace("_", " ").title()

            html += f"""
                <div class="recommendation-card">
                    <div class="rec-header">#{i} Priority: {display_name}</div>
                    <div class="rec-body">
                        <p><strong>Marginal Value:</strong> ${shadow_price:.2f} per unit{' (normalized)' if batch_size else ''}</p>
                        <p><strong>Recommendation:</strong> Expand capacity if cost per unit &lt; ${abs(shadow_price):.2f}</p>
                        <p><strong>ROI Estimate:</strong> Each additional unit of capacity generates ${abs(shadow_price):.2f} in profit</p>
                    </div>
                </div>
            """

        html += """
            </div>
        """
    else:
        html += """
            <p>Current capacity is well-balanced across all resources. No immediate capacity expansion needed.</p>
        """

    html += """
        </div>
    </div>
    """

    return html


def generate_summary_dashboard_html(stats: Dict, session) -> str:
    """Generate HTML for summary dashboard (same as Step 4)."""
    periods = session.query(Period).order_by(Period.week_number).all()

    max_profit = max(stats["profit_by_period"].values()) if stats["profit_by_period"] else 1
    profit_bars_html = ""
    for period in periods:
        profit = stats["profit_by_period"].get(period.id, 0)
        pct = (profit / max_profit * 100) if max_profit > 0 else 0
        profit_bars_html += f"""
        <div class="profit-bar-item">
            <div class="profit-bar-label">{period.name}</div>
            <div class="profit-bar-container">
                <div class="profit-bar-fill" style="width: {pct}%"></div>
                <span class="profit-bar-value">${profit:,.2f}</span>
            </div>
        </div>
        """

    p1_pct = (stats["order_fulfillment"][1]["satisfied"] / stats["order_fulfillment"][1]["total"] * 100) if stats["order_fulfillment"][1]["total"] > 0 else 0
    p2_pct = (stats["order_fulfillment"][2]["satisfied"] / stats["order_fulfillment"][2]["total"] * 100) if stats["order_fulfillment"][2]["total"] > 0 else 0
    p3_pct = (stats["order_fulfillment"][3]["satisfied"] / stats["order_fulfillment"][3]["total"] * 100) if stats["order_fulfillment"][3]["total"] > 0 else 0

    html = f"""
    <div class="dashboard-grid">
        <div class="stat-card">
            <h3>Total Profit</h3>
            <div class="stat-value">${stats['total_profit']:,.2f}</div>
            <div class="stat-label">Net Revenue</div>
        </div>
        <div class="stat-card">
            <h3>Products Manufactured</h3>
            <div class="stat-value">{stats['unique_products']}</div>
            <div class="stat-label">Unique Products</div>
        </div>
        <div class="stat-card">
            <h3>Production Runs</h3>
            <div class="stat-value">{stats['production_runs']}</div>
            <div class="stat-label">Total Batches</div>
        </div>
        <div class="stat-card">
            <h3>Planning Horizon</h3>
            <div class="stat-value">{stats['total_periods']}</div>
            <div class="stat-label">Weeks</div>
        </div>
    </div>

    <div class="dashboard-section">
        <h2>Profit by Period</h2>
        <div class="profit-bars">
            {profit_bars_html}
        </div>
    </div>

    <div class="dashboard-section">
        <h2>Resource Efficiency</h2>
        <div class="efficiency-grid">
            <div class="efficiency-card">
                <div class="efficiency-label">Machine Utilization</div>
                <div class="efficiency-gauge">
                    <div class="gauge-fill" style="width: {stats['overall_machine_util']:.1f}%"></div>
                </div>
                <div class="efficiency-value">{stats['overall_machine_util']:.1f}%</div>
            </div>
            <div class="efficiency-card">
                <div class="efficiency-label">Material Utilization</div>
                <div class="efficiency-gauge">
                    <div class="gauge-fill" style="width: {stats['overall_material_util']:.1f}%"></div>
                </div>
                <div class="efficiency-value">{stats['overall_material_util']:.1f}%</div>
            </div>
        </div>
    </div>

    <div class="dashboard-section">
        <h2>Order Fulfillment by Priority</h2>
        <div class="goal-satisfaction">
            <div class="goal-item">
                <div class="goal-header">
                    <span class="goal-label">Priority 1 (Gold Customers)</span>
                    <span class="goal-value">{stats['order_fulfillment'][1]['satisfied']}/{stats['order_fulfillment'][1]['total']} ({p1_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {p1_pct}%"></div>
                </div>
            </div>
            <div class="goal-item">
                <div class="goal-header">
                    <span class="goal-label">Priority 2 (Silver Customers)</span>
                    <span class="goal-value">{stats['order_fulfillment'][2]['satisfied']}/{stats['order_fulfillment'][2]['total']} ({p2_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {p2_pct}%"></div>
                </div>
            </div>
            <div class="goal-item">
                <div class="goal-header">
                    <span class="goal-label">Priority 3 (Bronze Customers)</span>
                    <span class="goal-value">{stats['order_fulfillment'][3]['satisfied']}/{stats['order_fulfillment'][3]['total']} ({p3_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {p3_pct}%"></div>
                </div>
            </div>
        </div>
    </div>
    """

    return html


def generate_production_schedule_html(production_data: Dict, inventory_data: Dict, session) -> str:
    """Generate HTML for production schedule view (same as Step 4)."""
    products = session.query(Product).all()
    periods = session.query(Period).order_by(Period.week_number).all()
    product_colors = generate_product_colors()

    html = """
    <div class="production-schedule">
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>Product</th>
    """

    for period in periods:
        html += f"<th>{period.name}<br/><span style='font-size:0.8rem;font-weight:normal'>Production</span></th>"
        html += f"<th>{period.name}<br/><span style='font-size:0.8rem;font-weight:normal'>Inventory</span></th>"

    html += "<th>Total<br/><span style='font-size:0.8rem;font-weight:normal'>Production</span></th>"
    html += "<th>Total<br/><span style='font-size:0.8rem;font-weight:normal'>Profit</span></th>"
    html += "</tr></thead><tbody>"

    for product in sorted(products, key=lambda p: p.name):
        color = product_colors.get(product.name, "#95a5a6")
        html += f"<tr><td class='product-name' style='border-left: 4px solid {color}'><strong>{product.name}</strong></td>"

        total_production = 0.0
        total_profit = 0.0

        for period in periods:
            prod_qty = production_data.get((product.id, period.id), 0.0)
            inv_qty = inventory_data.get((product.id, period.id), 0.0)
            profit = prod_qty * product.profit_per_unit

            total_production += prod_qty
            total_profit += profit

            if prod_qty > 0.01:
                html += f"<td class='production-cell has-production'>{prod_qty:.1f}</td>"
            else:
                html += "<td class='production-cell'>—</td>"

            if inv_qty > 0.01:
                html += f"<td class='inventory-cell has-inventory'>{inv_qty:.1f}</td>"
            else:
                html += "<td class='inventory-cell'>—</td>"

        html += f"<td class='total-cell'>{total_production:.1f}</td>"
        html += f"<td class='total-cell'>${total_profit:,.2f}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"

    return html


def generate_resource_utilization_html(stats: Dict, session) -> str:
    """Generate HTML for resource utilization view (same as Step 4)."""
    machines = session.query(Machine).all()
    materials = session.query(RawMaterial).all()
    periods = session.query(Period).order_by(Period.week_number).all()

    html = """
    <div class="resource-section">
        <h2>Machine Capacity Utilization</h2>
        <table class="resource-table">
            <thead>
                <tr>
                    <th>Machine</th>
    """

    for period in periods:
        html += f"<th>{period.name}</th>"

    html += "<th>Average</th></tr></thead><tbody>"

    for machine in sorted(machines, key=lambda m: m.name):
        html += f"<tr><td class='resource-name'><strong>{machine.name}</strong></td>"

        total_util = 0.0
        count = 0

        for period in periods:
            util_data = stats["machine_utilization"].get((machine.id, period.id), {"pct": 0, "used": 0, "available": 0})
            pct = util_data["pct"]
            used = util_data["used"]
            available = util_data["available"]

            total_util += pct
            count += 1

            color_class = "util-high" if pct > 90 else ("util-medium" if pct > 70 else "util-low")

            html += f"""
            <td class='util-cell {color_class}'>
                <div class='util-bar' style='width: {pct:.1f}%'></div>
                <span class='util-text'>{pct:.1f}%</span>
                <div class='util-tooltip'>{used:.1f}h / {available:.1f}h</div>
            </td>
            """

        avg_util = total_util / count if count > 0 else 0
        avg_color_class = "util-high" if avg_util > 90 else ("util-medium" if avg_util > 70 else "util-low")
        html += f"""
        <td class='util-cell {avg_color_class}'>
            <div class='util-bar' style='width: {avg_util:.1f}%'></div>
            <span class='util-text'>{avg_util:.1f}%</span>
        </td>
        """
        html += "</tr>"

    html += "</tbody></table></div>"

    html += """
    <div class="resource-section" style="margin-top: 30px;">
        <h2>Material Consumption</h2>
        <table class="resource-table">
            <thead>
                <tr>
                    <th>Material</th>
    """

    for period in periods:
        html += f"<th>{period.name}</th>"

    html += "<th>Total Used</th></tr></thead><tbody>"

    for material in sorted(materials, key=lambda m: m.name):
        html += f"<tr><td class='resource-name'><strong>{material.name}</strong></td>"

        total_used = 0.0

        for period in periods:
            cons_data = stats["material_consumption"].get((material.id, period.id), {"used": 0, "available": 0, "pct": 0})
            used = cons_data["used"]
            available = cons_data["available"]
            pct = cons_data["pct"]

            total_used += used

            color_class = "util-high" if pct > 90 else ("util-medium" if pct > 70 else "util-low")

            html += f"""
            <td class='util-cell {color_class}'>
                <div class='util-bar' style='width: {pct:.1f}%'></div>
                <span class='util-text'>{used:.1f}</span>
                <div class='util-tooltip'>{pct:.1f}% of {available:.1f}</div>
            </td>
            """

        html += f"<td class='total-cell'>{total_used:.1f}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"

    return html


def generate_order_fulfillment_html(production_data: Dict, session) -> str:
    """Generate HTML for order fulfillment view (same as Step 4)."""
    orders = session.query(CustomerOrder).all()
    customers = {c.id: c for c in session.query(Customer).all()}
    products = {p.id: p for p in session.query(Product).all()}
    periods = {per.id: per for per in session.query(Period).all()}

    orders_by_priority = {1: [], 2: [], 3: []}
    for order in orders:
        orders_by_priority[order.priority].append(order)

    priority_names = {1: "Priority 1 (Gold)", 2: "Priority 2 (Silver)", 3: "Priority 3 (Bronze)"}
    priority_badges = {1: "gold-badge", 2: "silver-badge", 3: "bronze-badge"}

    html = """
    <div class="orders-section">
    """

    for priority in [1, 2, 3]:
        html += f"""
        <div class="priority-section">
            <h2><span class="priority-badge {priority_badges[priority]}">{priority_names[priority]}</span></h2>
            <table class="orders-table">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Product</th>
                        <th>Period</th>
                        <th>Target Qty</th>
                        <th>Actual Qty</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        """

        for order in sorted(orders_by_priority[priority], key=lambda o: (o.customer_id, o.period_id)):
            customer = customers.get(order.customer_id)
            product = products.get(order.product_id)
            period = periods.get(order.period_id)

            customer_name = customer.name if customer else "Unknown"
            product_name = product.name if product else "Unknown"
            period_name = period.name if period else "Unknown"

            actual_qty = production_data.get((order.product_id, order.period_id), 0.0)
            shortfall = max(0, order.target_quantity - actual_qty)
            fulfilled = actual_qty >= order.target_quantity - 0.01

            status_class = "status-fulfilled" if fulfilled else "status-partial"
            status_icon = "✓" if fulfilled else "✗"
            status_text = "Fulfilled" if fulfilled else f"Short {shortfall:.1f}"

            html += f"""
                <tr class='{status_class}'>
                    <td>{customer_name}</td>
                    <td>{product_name}</td>
                    <td>{period_name}</td>
                    <td>{order.target_quantity:.1f}</td>
                    <td>{actual_qty:.1f}</td>
                    <td class='status-cell'>{status_icon} {status_text}</td>
                </tr>
            """

        html += "</tbody></table></div>"

    html += "</div>"

    return html


def generate_investment_strategy_html(sensitivity_data: Dict, stats: Dict, session) -> str:
    """Generate HTML for investment strategy recommendations.

    Args:
        sensitivity_data: Sensitivity analysis results
        stats: Statistics dictionary
        session: SQLAlchemy Session

    Returns:
        HTML string for investment strategy tab
    """
    top_sensitive = sensitivity_data["top_sensitive"]
    num_binding = sensitivity_data["num_binding"]
    normalize_fn = sensitivity_data["normalize_shadow_price"]

    html = """
    <div class="investment-strategy">
        <h2>Strategic Investment Roadmap</h2>
        <div class="info-box">
            <p><strong>Investment Strategy Based on Sensitivity Analysis</strong></p>
            <p>This analysis uses shadow prices (marginal values) from the optimization solution to prioritize
            capacity expansion investments. Shadow prices represent the expected profit increase per unit of
            additional capacity.</p>
            <p><strong>Note:</strong> Shadow prices for batch constraints are normalized by dividing by the minimum batch size
            to show the actual marginal value per constraint unit.</p>
        </div>

        <div class="dashboard-section">
            <h2>Investment Priority Matrix</h2>
            <table class="investment-matrix-table">
                <thead>
                    <tr>
                        <th style="width: 50px;">Rank</th>
                        <th>Resource / Constraint</th>
                        <th>Marginal Value ($/unit)</th>
                        <th>Priority Level</th>
                        <th>Investment Decision</th>
                        <th>Expected Annual ROI</th>
                    </tr>
                </thead>
                <tbody>
    """

    if top_sensitive:
        for i, (name, sens) in enumerate(top_sensitive[:10], 1):
            raw_shadow_price = sens.shadow_price or 0.0

            # Normalize shadow price for batch constraints
            normalized_shadow_price, batch_size = normalize_fn(name, raw_shadow_price)
            shadow_price = normalized_shadow_price

            # Determine priority level based on normalized value
            if abs(shadow_price) > 1.0:
                priority = "HIGH"
                priority_class = "priority-high"
                decision = "Invest immediately"
                recommendation_icon = "🔴"
            elif abs(shadow_price) > 0.1:
                priority = "MEDIUM"
                priority_class = "priority-medium"
                decision = "Consider investment"
                recommendation_icon = "🟡"
            else:
                priority = "LOW"
                priority_class = "priority-low"
                decision = "Monitor only"
                recommendation_icon = "🟢"

            # Format constraint name for display
            display_name = name.replace("_", " ").title()

            # Estimate annual ROI (assuming weekly capacity * 52 weeks)
            annual_roi = abs(shadow_price) * 52

            html += f"""
                <tr class="investment-row">
                    <td class="rank-cell">{recommendation_icon} #{i}</td>
                    <td class="resource-name">{display_name}</td>
                    <td class="value-cell">${shadow_price:.2f}{' (÷' + str(int(batch_size)) + ')' if batch_size else ''}</td>
                    <td><span class="priority-badge {priority_class}">{priority}</span></td>
                    <td class="decision-cell">{decision}</td>
                    <td class="roi-cell">${annual_roi:,.2f}</td>
                </tr>
            """
    else:
        html += """
                <tr>
                    <td colspan="6" style="text-align: center; padding: 30px;">
                        No capacity constraints identified. Current capacity is sufficient.
                    </td>
                </tr>
        """

    html += """
                </tbody>
            </table>
        </div>

        <div class="dashboard-section" style="margin-top: 30px;">
            <h2>Detailed Investment Recommendations</h2>
            <div class="recommendation-grid">
    """

    # Top 3 detailed recommendations
    if top_sensitive and len(top_sensitive) > 0:
        for i, (name, sens) in enumerate(top_sensitive[:3], 1):
            raw_shadow_price = sens.shadow_price or 0.0
            normalized_shadow_price, batch_size = normalize_fn(name, raw_shadow_price)
            shadow_price = normalized_shadow_price
            display_name = name.replace("_", " ").title()

            # Parse resource type
            if "machine" in name.lower():
                resource_type = "Machine Capacity"
                investment_example = "Purchase additional equipment or extend operating hours"
            elif "material" in name.lower():
                resource_type = "Material Supply"
                investment_example = "Negotiate larger supplier contracts or find additional suppliers"
            elif "batch" in name.lower():
                resource_type = "Batch Size Constraint"
                investment_example = "Increase minimum batch size flexibility or reduce setup costs"
            else:
                resource_type = "Resource Capacity"
                investment_example = "Expand capacity through various means"

            annual_roi = abs(shadow_price) * 52

            if abs(shadow_price) > 1.0:
                urgency = "Immediate Action Required"
                urgency_color = "#e74c3c"
            elif abs(shadow_price) > 0.1:
                urgency = "Near-Term Investment"
                urgency_color = "#f39c12"
            else:
                urgency = "Long-Term Consideration"
                urgency_color = "#95a5a6"

            normalized_note = f" (normalized by ÷{int(batch_size)})" if batch_size else ""

            html += f"""
                <div class="recommendation-card">
                    <div class="rec-header" style="background: {urgency_color};">
                        #{i} Investment Priority: {display_name}
                    </div>
                    <div class="rec-body">
                        <p><strong>Resource Type:</strong> {resource_type}</p>
                        <p><strong>Current Status:</strong> Operating at capacity (binding constraint)</p>
                        <p><strong>Marginal Value:</strong> ${shadow_price:.2f} per unit{normalized_note}</p>
                        <p><strong>Annual ROI Estimate:</strong> ${annual_roi:,.2f} per unit/year</p>
                        <p><strong>Urgency:</strong> <span style="color: {urgency_color}; font-weight: bold;">{urgency}</span></p>
                        <p><strong>Investment Options:</strong> {investment_example}</p>
                        <p><strong>Break-even Analysis:</strong> Investment pays for itself if cost per unit &lt; ${abs(shadow_price):.2f}/week</p>
                    </div>
                </div>
            """

    html += """
            </div>
        </div>

        <div class="dashboard-section" style="margin-top: 30px;">
            <h2>Risk & Portfolio Balance</h2>
    """

    # Risk assessment
    if num_binding >= 10:
        risk_level = "HIGH RISK"
        risk_color = "#e74c3c"
        risk_message = f"""
            <p><strong>⚠️ High Sensitivity Detected:</strong> {num_binding} binding constraints identified.</p>
            <ul>
                <li>The production system is operating at or near capacity on multiple resources</li>
                <li>Small disruptions can significantly impact profit</li>
                <li><strong>Recommendation:</strong> Diversify capacity investments across multiple resources</li>
                <li><strong>Portfolio Strategy:</strong> Invest in top 3-5 constraints rather than just the top one</li>
            </ul>
        """
    elif num_binding >= 5:
        risk_level = "MODERATE RISK"
        risk_color = "#f39c12"
        risk_message = f"""
            <p><strong>⚡ Moderate Sensitivity:</strong> {num_binding} binding constraints identified.</p>
            <ul>
                <li>Some resources are at capacity while others have slack</li>
                <li><strong>Recommendation:</strong> Focus on top 2-3 bottlenecks for balanced growth</li>
                <li><strong>Portfolio Strategy:</strong> Targeted investments in highest-value constraints</li>
            </ul>
        """
    else:
        risk_level = "LOW RISK"
        risk_color = "#27ae60"
        risk_message = f"""
            <p><strong>✓ Low Sensitivity:</strong> Only {num_binding} binding constraints.</p>
            <ul>
                <li>System has good capacity buffer in most resources</li>
                <li><strong>Recommendation:</strong> Focus on highest marginal value opportunity</li>
                <li><strong>Portfolio Strategy:</strong> Selective investment in #1 priority if ROI is attractive</li>
            </ul>
        """

    html += f"""
            <div style="padding: 20px; background: {risk_color}22; border-left: 4px solid {risk_color}; border-radius: 4px;">
                <h3 style="color: {risk_color};">{risk_level}</h3>
                {risk_message}
            </div>
        </div>

        <div class="dashboard-section" style="margin-top: 30px;">
            <h2>Implementation Timeline</h2>
            <div style="background: white; padding: 25px; border-radius: 8px;">
                <h3>Recommended Phased Approach</h3>

                <div style="margin: 20px 0;">
                    <h4 style="color: #e74c3c;">Phase 1 (Immediate - Next Quarter)</h4>
                    <p>Focus on high-priority (shadow price &gt; $1.00) bottlenecks:</p>
                    <ul>
    """

    # Phase 1: High priority
    phase1_count = 0
    if top_sensitive:
        for name, sens in top_sensitive[:10]:
            raw_shadow_price = sens.shadow_price or 0.0
            normalized_shadow_price, batch_size = normalize_fn(name, raw_shadow_price)
            if abs(normalized_shadow_price) > 1.0:
                display_name = name.replace("_", " ").title()
                normalized_note = f" (÷{int(batch_size)})" if batch_size else ""
                html += f"<li>{display_name} (Marginal value: ${normalized_shadow_price:.2f}/unit{normalized_note})</li>"
                phase1_count += 1

    if phase1_count == 0:
        html += "<li>No immediate high-priority investments identified</li>"

    html += """
                    </ul>
                </div>

                <div style="margin: 20px 0;">
                    <h4 style="color: #f39c12;">Phase 2 (Near-term - 2-4 Quarters)</h4>
                    <p>Address medium-priority (shadow price $0.10-$1.00) constraints:</p>
                    <ul>
    """

    # Phase 2: Medium priority
    phase2_count = 0
    if top_sensitive:
        for name, sens in top_sensitive[:10]:
            raw_shadow_price = sens.shadow_price or 0.0
            normalized_shadow_price, batch_size = normalize_fn(name, raw_shadow_price)
            if 0.1 <= abs(normalized_shadow_price) <= 1.0:
                display_name = name.replace("_", " ").title()
                normalized_note = f" (÷{int(batch_size)})" if batch_size else ""
                html += f"<li>{display_name} (Marginal value: ${normalized_shadow_price:.2f}/unit{normalized_note})</li>"
                phase2_count += 1

    if phase2_count == 0:
        html += "<li>No medium-priority investments identified</li>"

    html += """
                    </ul>
                </div>

                <div style="margin: 20px 0;">
                    <h4 style="color: #27ae60;">Phase 3 (Long-term - Beyond 4 Quarters)</h4>
                    <p>Monitor and reassess:</p>
                    <ul>
                        <li>Re-run sensitivity analysis after Phase 1-2 implementations</li>
                        <li>Priorities may shift after capacity changes</li>
                        <li>New bottlenecks may emerge</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """

    return html


def generate_html_report(solution, session, analyzer, output_path: str = "production_sensitivity_report.html"):
    """Generate comprehensive interactive HTML report with sensitivity analysis.

    Args:
        solution: LXSolution object from optimization
        session: SQLAlchemy Session for database access
        analyzer: LXSensitivityAnalyzer for sensitivity analysis
        output_path: Path where HTML file will be saved
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution to generate report from!")
        return

    print("\n" + "=" * 80)
    print("GENERATING INTERACTIVE HTML REPORT WITH SENSITIVITY ANALYSIS")
    print("=" * 80)

    # Extract data
    production_data = extract_production_data(solution, session)
    inventory_data = extract_inventory_data(solution, session)
    stats = calculate_statistics(solution, session, production_data, inventory_data)
    sensitivity_data = extract_sensitivity_data(analyzer, session)

    print(f"  Extracting production data...")
    print(f"  Extracting sensitivity data...")
    print(f"  Calculating statistics...")

    # Generate view HTML
    summary_html = generate_summary_dashboard_html(stats, session)
    sensitivity_dashboard_html = generate_sensitivity_dashboard_html(sensitivity_data, stats)
    shadow_price_html = generate_shadow_price_analysis_html(sensitivity_data, session)
    bottleneck_html = generate_bottleneck_analysis_html(sensitivity_data)
    investment_strategy_html = generate_investment_strategy_html(sensitivity_data, stats, session)
    schedule_html = generate_production_schedule_html(production_data, inventory_data, session)
    resources_html = generate_resource_utilization_html(stats, session)
    orders_html = generate_order_fulfillment_html(production_data, session)

    print(f"  Generating summary dashboard...")
    print(f"  Generating sensitivity dashboard...")
    print(f"  Generating shadow price analysis...")
    print(f"  Generating bottleneck analysis...")
    print(f"  Generating investment strategy...")
    print(f"  Generating production schedule...")
    print(f"  Generating resource utilization...")
    print(f"  Generating order fulfillment...")

    # Complete HTML document with sensitivity analysis styling
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Production Planning with Sensitivity Analysis - LumiX</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}

        .tabs {{
            display: flex;
            flex-wrap: wrap;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            gap: 5px;
            padding: 10px 10px 0 10px;
        }}

        .tab {{
            padding: 12px 20px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 0.95rem;
            font-weight: 600;
            color: #6c757d;
            transition: all 0.3s ease;
            white-space: nowrap;
            border-radius: 8px 8px 0 0;
            margin-bottom: -2px;
        }}

        .tab:hover {{
            background: rgba(17, 153, 142, 0.1);
            color: #11998e;
        }}

        .tab.active {{
            color: #11998e;
            border-bottom: 3px solid #11998e;
            background: white;
        }}

        .tab-content {{
            display: none;
            padding: 30px;
            animation: fadeIn 0.3s ease;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .stat-card.sensitivity-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}

        .stat-card h3 {{
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin: 10px 0;
        }}

        .stat-label {{
            font-size: 0.9rem;
            opacity: 0.8;
        }}

        .dashboard-section {{
            margin: 30px 0;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 12px;
        }}

        .dashboard-section h2 {{
            color: #11998e;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }}

        .info-box {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}

        .info-box p {{
            margin: 10px 0;
            line-height: 1.6;
        }}

        .info-box ul {{
            margin: 10px 0 10px 20px;
            line-height: 1.8;
        }}

        .profit-bars {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .profit-bar-item {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .profit-bar-label {{
            min-width: 100px;
            font-weight: 600;
            color: #495057;
        }}

        .profit-bar-container {{
            flex: 1;
            height: 40px;
            background: #e9ecef;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
        }}

        .profit-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            padding-right: 10px;
            justify-content: flex-end;
        }}

        .profit-bar-value {{
            color: white;
            font-weight: 700;
            font-size: 0.9rem;
        }}

        .efficiency-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}

        .efficiency-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}

        .efficiency-label {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 15px;
        }}

        .efficiency-gauge {{
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 10px;
        }}

        .gauge-fill {{
            height: 100%;
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            transition: width 0.5s ease;
        }}

        .efficiency-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #11998e;
        }}

        .goal-satisfaction {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .goal-item {{
            background: white;
            padding: 20px;
            border-radius: 8px;
        }}

        .goal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .goal-label {{
            font-weight: 600;
            color: #495057;
        }}

        .goal-value {{
            font-weight: 700;
            color: #11998e;
        }}

        .progress-bar {{
            width: 100%;
            height: 12px;
            background: #e9ecef;
            border-radius: 6px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            transition: width 0.5s ease;
        }}

        .production-schedule {{
            overflow-x: auto;
        }}

        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .schedule-table th {{
            background: #11998e;
            color: white;
            padding: 15px 10px;
            text-align: center;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.85rem;
        }}

        .schedule-table td {{
            padding: 12px 10px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}

        .product-name {{
            text-align: left;
            background: #f8f9fa;
            font-weight: 700;
        }}

        .production-cell {{
            background: #e3f2fd;
        }}

        .production-cell.has-production {{
            background: #c8e6c9;
            font-weight: 600;
        }}

        .inventory-cell {{
            background: #fff3e0;
        }}

        .inventory-cell.has-inventory {{
            background: #ffe082;
            font-weight: 600;
        }}

        .total-cell {{
            background: #f8f9fa;
            font-weight: 700;
            color: #11998e;
        }}

        .resource-section {{
            margin: 20px 0;
        }}

        .resource-section h2 {{
            color: #11998e;
            margin-bottom: 15px;
        }}

        .resource-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .resource-table th {{
            background: #11998e;
            color: white;
            padding: 12px 10px;
            text-align: center;
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .resource-table td {{
            padding: 10px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}

        .resource-name {{
            text-align: left;
            background: #f8f9fa;
            font-weight: 700;
        }}

        .util-cell {{
            position: relative;
            padding: 5px;
        }}

        .util-bar {{
            height: 20px;
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            border-radius: 4px;
            transition: width 0.3s ease;
        }}

        .util-text {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-weight: 700;
            font-size: 0.85rem;
            color: #333;
        }}

        .util-tooltip {{
            display: none;
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            white-space: nowrap;
            z-index: 100;
        }}

        .util-cell:hover .util-tooltip {{
            display: block;
        }}

        .util-low .util-bar {{
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
        }}

        .util-medium .util-bar {{
            background: linear-gradient(90deg, #f39c12 0%, #f1c40f 100%);
        }}

        .util-high .util-bar {{
            background: linear-gradient(90deg, #e74c3c 0%, #c0392b 100%);
        }}

        .priority-section {{
            margin: 30px 0;
        }}

        .priority-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 1.1rem;
        }}

        .gold-badge {{
            background: linear-gradient(135deg, #f39c12 0%, #f1c40f 100%);
            color: white;
        }}

        .silver-badge {{
            background: linear-gradient(135deg, #95a5a6 0%, #bdc3c7 100%);
            color: white;
        }}

        .bronze-badge {{
            background: linear-gradient(135deg, #cd7f32 0%, #b8732d 100%);
            color: white;
        }}

        .orders-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-top: 15px;
        }}

        .orders-table th {{
            background: #11998e;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .orders-table td {{
            padding: 10px;
            border: 1px solid #dee2e6;
        }}

        .status-cell {{
            font-weight: 700;
            text-align: center;
        }}

        .status-fulfilled {{
            background: #d4edda;
        }}

        .status-fulfilled .status-cell {{
            color: #155724;
        }}

        .status-partial {{
            background: #fff3cd;
        }}

        .status-partial .status-cell {{
            color: #856404;
        }}

        /* Sensitivity Analysis Specific Styles */
        .shadow-price-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin: 20px 0;
        }}

        .shadow-price-table th {{
            background: #667eea;
            color: white;
            padding: 12px 10px;
            text-align: center;
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .shadow-price-table td {{
            padding: 10px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}

        .shadow-cell {{
            position: relative;
            padding: 10px;
        }}

        .shadow-value {{
            font-weight: 600;
        }}

        .shadow-tooltip {{
            display: none;
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 0.75rem;
            white-space: nowrap;
            z-index: 100;
            line-height: 1.6;
        }}

        .shadow-cell:hover .shadow-tooltip {{
            display: block;
        }}

        .shadow-high {{
            background: #ffe0e0;
        }}

        .shadow-medium {{
            background: #fff3cd;
        }}

        .shadow-low {{
            background: #e8e8e8;
        }}

        .avg-cell {{
            background: #f0f0f0;
            font-weight: 700;
            color: #667eea;
        }}

        .bottleneck-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin: 20px 0;
        }}

        .bottleneck-table th {{
            background: #667eea;
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .bottleneck-row td {{
            padding: 15px;
            border: 1px solid #dee2e6;
        }}

        .rank-cell {{
            font-weight: 700;
            font-size: 1.1rem;
            color: #667eea;
            text-align: center;
        }}

        .constraint-name {{
            font-weight: 600;
        }}

        .shadow-price-cell {{
            font-weight: 700;
            color: #e74c3c;
        }}

        .impact-cell {{
            color: #27ae60;
            font-weight: 600;
        }}

        .priority-badge.priority-high {{
            background: #e74c3c;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
        }}

        .priority-badge.priority-medium {{
            background: #f39c12;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
        }}

        .priority-badge.priority-low {{
            background: #95a5a6;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
        }}

        .recommendation-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .recommendation-card {{
            background: white;
            border-left: 4px solid #667eea;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            overflow: hidden;
        }}

        .rec-header {{
            background: #667eea;
            color: white;
            padding: 15px;
            font-weight: 700;
            font-size: 1.1rem;
        }}

        .rec-body {{
            padding: 20px;
        }}

        .rec-body p {{
            margin: 10px 0;
            line-height: 1.6;
        }}

        /* Investment Strategy Styles */
        .investment-matrix-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin: 20px 0;
        }}

        .investment-matrix-table th {{
            background: #667eea;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .investment-matrix-table td {{
            padding: 15px 10px;
            border: 1px solid #dee2e6;
        }}

        .investment-row {{
            transition: background 0.2s ease;
        }}

        .investment-row:hover {{
            background: #f8f9fa;
        }}

        .value-cell {{
            font-weight: 700;
            color: #e74c3c;
            text-align: center;
        }}

        .decision-cell {{
            font-weight: 600;
            color: #667eea;
        }}

        .roi-cell {{
            font-weight: 700;
            color: #27ae60;
            text-align: right;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            header h1 {{
                font-size: 1.8rem;
            }}

            .tabs {{
                gap: 3px;
                padding: 5px 5px 0 5px;
            }}

            .tab {{
                padding: 10px 15px;
                font-size: 0.85rem;
                flex: 1 1 auto;
                text-align: center;
            }}

            .tab-content {{
                padding: 15px;
            }}

            .stat-value {{
                font-size: 2rem;
            }}

            .investment-matrix-table {{
                font-size: 0.8rem;
            }}

            .recommendation-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Multi-Period Production Planning with Sensitivity Analysis</h1>
            <p>Interactive Optimization Dashboard with Business Insights - Generated by LumiX</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab(event, 'summary')">Summary Dashboard</button>
            <button class="tab" onclick="showTab(event, 'sensitivity')">Sensitivity Analysis</button>
            <button class="tab" onclick="showTab(event, 'shadowprices')">Shadow Prices</button>
            <button class="tab" onclick="showTab(event, 'bottlenecks')">Bottlenecks</button>
            <button class="tab" onclick="showTab(event, 'investment')">Investment Strategy</button>
            <button class="tab" onclick="showTab(event, 'schedule')">Production Schedule</button>
            <button class="tab" onclick="showTab(event, 'resources')">Resource Utilization</button>
            <button class="tab" onclick="showTab(event, 'orders')">Customer Orders</button>
        </div>

        <div id="summary" class="tab-content active">
            <h2>Summary Dashboard</h2>
            {summary_html}
        </div>

        <div id="sensitivity" class="tab-content">
            <h2>Sensitivity Analysis Dashboard</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Key sensitivity metrics and solution robustness assessment</p>
            {sensitivity_dashboard_html}
        </div>

        <div id="shadowprices" class="tab-content">
            <h2>Shadow Price Analysis</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Marginal value of each resource constraint</p>
            {shadow_price_html}
        </div>

        <div id="bottlenecks" class="tab-content">
            <h2>Bottleneck Identification & Investment Recommendations</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Prioritized list of capacity expansion opportunities</p>
            {bottleneck_html}
        </div>

        <div id="investment" class="tab-content">
            <h2>Investment Strategy</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Strategic investment roadmap based on sensitivity analysis</p>
            {investment_strategy_html}
        </div>

        <div id="schedule" class="tab-content">
            <h2>Production Schedule</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Multi-period production plan with inventory tracking</p>
            {schedule_html}
        </div>

        <div id="resources" class="tab-content">
            <h2>Resource Utilization</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Machine capacity and material consumption analysis</p>
            {resources_html}
        </div>

        <div id="orders" class="tab-content">
            <h2>Customer Order Fulfillment</h2>
            <p style="margin-bottom: 20px; color: #6c757d;">Order satisfaction by customer priority</p>
            {orders_html}
        </div>
    </div>

    <script>
        function showTab(evt, tabName) {{
            // Hide all tab content
            var tabContents = document.getElementsByClassName('tab-content');
            for (var i = 0; i < tabContents.length; i++) {{
                tabContents[i].style.display = 'none';
                tabContents[i].classList.remove('active');
            }}

            // Remove active class from all tabs
            var tabs = document.getElementsByClassName('tab');
            for (var i = 0; i < tabs.length; i++) {{
                tabs[i].classList.remove('active');
            }}

            // Show the selected tab content
            var selectedTab = document.getElementById(tabName);
            if (selectedTab) {{
                selectedTab.style.display = 'block';
                selectedTab.classList.add('active');
            }}

            // Add active class to the clicked tab button
            if (evt && evt.currentTarget) {{
                evt.currentTarget.classList.add('active');
            }}
        }}

        // Initialize on page load - show summary tab
        window.onload = function() {{
            var summaryTab = document.getElementById('summary');
            if (summaryTab) {{
                summaryTab.style.display = 'block';
            }}
        }};
    </script>
</body>
</html>"""

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n  ✓ HTML report generated: {output_path}")
    print(f"  ✓ Status: {solution.status}")
    print(f"  ✓ Total Profit: ${stats['total_profit']:,.2f}")
    print(f"  ✓ Binding Constraints: {sensitivity_data['num_binding']}")
    print(f"  ✓ Bottlenecks Identified: {sensitivity_data['num_bottlenecks']}")
    print("=" * 80)
