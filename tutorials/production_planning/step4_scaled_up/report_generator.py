"""Interactive HTML Report Generator for Production Planning Solutions.

This module generates a modern, interactive HTML5 + CSS dashboard for visualizing
multi-period production optimization results with comprehensive analytics.

Features:
    - Summary dashboard with key performance metrics
    - Multi-period production schedule with weekly breakdown
    - Resource utilization analysis (machines & materials)
    - Customer order fulfillment tracking by priority
    - Financial breakdown with cost analysis
    - Color-coded visualizations with consistent palette
    - Interactive tab navigation
    - Responsive design for different screen sizes
    - Self-contained single HTML file (no external dependencies)

Usage:
    >>> from report_generator import generate_html_report
    >>> generate_html_report(solution, session, "production_report.html")
"""

from typing import Dict, List, Tuple, Any
from database import (
    Product,
    Period,
    Machine,
    RawMaterial,
    Customer,
    CustomerOrder,
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
)


def extract_production_data(solution, session) -> Dict[Tuple[int, int], float]:
    """Extract production quantities from solution.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session

    Returns:
        Dictionary mapping (product_id, period_id) to production quantity
    """
    production_data = {}
    for (product_id, period_id), value in solution.variables["production"].items():
        if value > 0.01:  # Only include non-trivial production
            production_data[(product_id, period_id)] = value
    return production_data


def extract_inventory_data(solution, session) -> Dict[Tuple[int, int], float]:
    """Extract inventory levels from solution.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session

    Returns:
        Dictionary mapping (product_id, period_id) to inventory quantity
    """
    inventory_data = {}
    for (product_id, period_id), value in solution.variables["inventory"].items():
        inventory_data[(product_id, period_id)] = value
    return inventory_data


def calculate_statistics(solution, session, production_data: Dict, inventory_data: Dict) -> Dict[str, Any]:
    """Calculate summary statistics for the dashboard.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session
        production_data: Extracted production quantities
        inventory_data: Extracted inventory levels

    Returns:
        Dictionary containing various statistics
    """
    products = session.query(Product).all()
    periods = session.query(Period).order_by(Period.week_number).all()
    machines = session.query(Machine).all()
    materials = session.query(RawMaterial).all()
    orders = session.query(CustomerOrder).all()

    # Create cached helpers
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

    # Count production runs (products produced per period)
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

    # Calculate overall machine utilization
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

    # Calculate overall material utilization
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

    # Count unique products manufactured
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
    """Generate consistent color palette for products.

    Returns:
        Dictionary mapping product names to hex color codes
    """
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


def generate_summary_dashboard_html(stats: Dict, session) -> str:
    """Generate HTML for summary dashboard.

    Args:
        stats: Statistics dictionary
        session: SQLAlchemy Session

    Returns:
        HTML string for summary dashboard
    """
    periods = session.query(Period).order_by(Period.week_number).all()

    # Create profit bars
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

    # Order fulfillment percentages
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
    """Generate HTML for production schedule view.

    Args:
        production_data: Production quantities
        inventory_data: Inventory levels
        session: SQLAlchemy Session

    Returns:
        HTML string for production schedule
    """
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

            # Production cell
            if prod_qty > 0.01:
                html += f"<td class='production-cell has-production'>{prod_qty:.1f}</td>"
            else:
                html += "<td class='production-cell'>—</td>"

            # Inventory cell
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
    """Generate HTML for resource utilization view.

    Args:
        stats: Statistics dictionary
        session: SQLAlchemy Session

    Returns:
        HTML string for resource utilization
    """
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
    """Generate HTML for order fulfillment view.

    Args:
        production_data: Production quantities
        session: SQLAlchemy Session

    Returns:
        HTML string for order fulfillment
    """
    orders = session.query(CustomerOrder).all()
    customers = {c.id: c for c in session.query(Customer).all()}
    products = {p.id: p for p in session.query(Product).all()}
    periods = {per.id: per for per in session.query(Period).all()}

    # Group orders by priority
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


def generate_html_report(solution, session, output_path: str = "production_report.html"):
    """Generate comprehensive interactive HTML report for production planning solution.

    Creates a modern, self-contained HTML5 + CSS dashboard with multiple views:
    - Summary dashboard with key metrics
    - Multi-period production schedule
    - Resource utilization analysis
    - Customer order fulfillment tracking

    Args:
        solution: LXSolution object from optimization
        session: SQLAlchemy Session for database access
        output_path: Path where HTML file will be saved

    Example:
        >>> from report_generator import generate_html_report
        >>> generate_html_report(solution, session, "report.html")
        HTML report generated: report.html

    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution to generate report from!")
        return

    print("\n" + "=" * 80)
    print("GENERATING INTERACTIVE HTML REPORT")
    print("=" * 80)

    # Extract data
    production_data = extract_production_data(solution, session)
    inventory_data = extract_inventory_data(solution, session)
    stats = calculate_statistics(solution, session, production_data, inventory_data)

    print(f"  Extracting production data...")
    print(f"  Calculating statistics...")

    # Generate view HTML
    summary_html = generate_summary_dashboard_html(stats, session)
    schedule_html = generate_production_schedule_html(production_data, inventory_data, session)
    resources_html = generate_resource_utilization_html(stats, session)
    orders_html = generate_order_fulfillment_html(production_data, session)

    print(f"  Generating summary dashboard...")
    print(f"  Generating production schedule...")
    print(f"  Generating resource utilization...")
    print(f"  Generating order fulfillment...")

    # Complete HTML document
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Production Planning Report - Multi-Period Optimization</title>
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
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            overflow-x: auto;
        }}

        .tab {{
            padding: 18px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1rem;
            font-weight: 600;
            color: #6c757d;
            transition: all 0.3s ease;
            white-space: nowrap;
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

        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            header h1 {{
                font-size: 1.8rem;
            }}

            .tab {{
                padding: 12px 20px;
                font-size: 0.9rem;
            }}

            .tab-content {{
                padding: 15px;
            }}

            .stat-value {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Multi-Period Production Planning Report</h1>
            <p>Interactive Manufacturing Optimization Dashboard - Generated by LumiX</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('summary')">Summary Dashboard</button>
            <button class="tab" onclick="showTab('schedule')">Production Schedule</button>
            <button class="tab" onclick="showTab('resources')">Resource Utilization</button>
            <button class="tab" onclick="showTab('orders')">Customer Orders</button>
        </div>

        <div id="summary" class="tab-content active">
            <h2>Summary Dashboard</h2>
            {summary_html}
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
        function showTab(tabName) {{
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));

            // Deactivate all tabs
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));

            // Show selected tab content
            document.getElementById(tabName).classList.add('active');

            // Activate selected tab
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>"""

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n  ✓ HTML report generated: {output_path}")
    print(f"  ✓ Status: {solution.status}")
    print(f"  ✓ Total Profit: ${stats['total_profit']:,.2f}")
    print(f"  ✓ Production Runs: {stats['production_runs']}")
    print("=" * 80)
