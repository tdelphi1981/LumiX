"""Interactive HTML Report Generator with What-If Analysis Visualizations.

This module extends Step 4's report generator with comprehensive what-if analysis
visualizations including bottleneck ranking, sensitivity curves, investment ROI
comparison, and risk assessment dashboards.

Features:
    - Summary dashboard with key performance metrics (from Step 4)
    - Multi-period production schedule with weekly breakdown (from Step 4)
    - Resource utilization analysis (machines & materials) (from Step 4)
    - Customer order fulfillment tracking by priority (from Step 4)
    - What-If Analysis Dashboard (NEW in Step 7):
        - Capacity change scenarios with profit impact
        - Bottleneck identification and ranking
        - Sensitivity curve visualizations
        - Investment ROI comparison charts
        - Risk assessment for downside scenarios
    - Color-coded visualizations with consistent palette
    - Interactive tab navigation
    - Responsive design for different screen sizes
    - Self-contained single HTML file (no external dependencies)

Usage:
    >>> from report_generator import generate_html_report
    >>> generate_html_report(solution, session, whatif_results, "report.html")
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
    """Extract production quantities from solution."""
    production_data = {}
    for (product_id, period_id), value in solution.variables["production"].items():
        if value > 0.01:  # Only include non-trivial production
            production_data[(product_id, period_id)] = value
    return production_data


def extract_inventory_data(solution, session) -> Dict[Tuple[int, int], float]:
    """Extract inventory levels from solution."""
    inventory_data = {}
    for (product_id, period_id), value in solution.variables["inventory"].items():
        inventory_data[(product_id, period_id)] = value
    return inventory_data


def calculate_statistics(solution, session, production_data: Dict, inventory_data: Dict) -> Dict[str, Any]:
    """Calculate summary statistics for the dashboard."""
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

    # Calculate order fulfillment
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


def generate_summary_dashboard_html(stats: Dict, session) -> str:
    """Generate HTML for summary dashboard (same as Step 4)."""
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


def generate_whatif_dashboard_html(whatif_results: Dict) -> str:
    """Generate HTML for what-if analysis dashboard (NEW in Step 7).

    Args:
        whatif_results: Dictionary containing all what-if analysis results

    Returns:
        HTML string for what-if analysis dashboard
    """
    baseline_profit = whatif_results.get("baseline_profit", 0)

    html = f"""
    <div class="whatif-intro">
        <p style="font-size: 1.1rem; color: #6c757d; margin-bottom: 30px;">
            This section presents the results of comprehensive what-if analysis, exploring how
            changes in capacity, materials, and other parameters impact the optimal solution.
            Use these insights to prioritize investments and prepare for risks.
        </p>
    </div>

    <div class="whatif-section">
        <h2>Baseline & Key Metrics</h2>
        <div class="whatif-metrics">
            <div class="whatif-metric-card">
                <div class="metric-label">Baseline Profit</div>
                <div class="metric-value">${baseline_profit:,.2f}</div>
                <div class="metric-sublabel">Optimal solution</div>
            </div>
            <div class="whatif-metric-card">
                <div class="metric-label">Scenarios Tested</div>
                <div class="metric-value">{len(whatif_results.get('capacity_changes', [])) + len(whatif_results.get('risk_scenarios', []))}</div>
                <div class="metric-sublabel">Capacity & risk scenarios</div>
            </div>
            <div class="whatif-metric-card">
                <div class="metric-label">Bottlenecks Found</div>
                <div class="metric-value">{len(whatif_results.get('bottlenecks', []))}</div>
                <div class="metric-sublabel">Resources analyzed</div>
            </div>
        </div>
    </div>

    <div class="whatif-section">
        <h2>Capacity Change Scenarios</h2>
        <p style="color: #6c757d; margin-bottom: 15px;">
            Impact of increasing resource capacity on profit
        </p>
        <table class="whatif-table">
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Change</th>
                    <th>Original Profit</th>
                    <th>New Profit</th>
                    <th>Delta</th>
                    <th>Change %</th>
                    <th>Marginal Value</th>
                </tr>
            </thead>
            <tbody>
    """

    for scenario in whatif_results.get("capacity_changes", []):
        delta_class = "positive-delta" if scenario["delta"] > 0 else "negative-delta"
        html += f"""
                <tr>
                    <td><strong>{scenario['description']}</strong></td>
                    <td>{scenario['change']:+.0f} units</td>
                    <td>${scenario['original_profit']:,.2f}</td>
                    <td>${scenario['new_profit']:,.2f}</td>
                    <td class="{delta_class}">${scenario['delta']:+,.2f}</td>
                    <td class="{delta_class}">{scenario['delta_pct']:+.2f}%</td>
                    <td><strong>${scenario['marginal_value']:.2f}/unit</strong></td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>

    <div class="whatif-section">
        <h2>Bottleneck Identification & Ranking</h2>
        <p style="color: #6c757d; margin-bottom: 15px;">
            Resources ranked by marginal value (profit increase per unit of capacity)
        </p>
        <table class="whatif-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Resource</th>
                    <th>Period</th>
                    <th>Type</th>
                    <th>Marginal Value</th>
                    <th>Priority</th>
                </tr>
            </thead>
            <tbody>
    """

    bottlenecks = whatif_results.get("bottlenecks", [])
    for i, bottleneck in enumerate(bottlenecks[:15], 1):  # Top 15
        priority_class = f"priority-{bottleneck['priority'].lower()}"
        html += f"""
                <tr>
                    <td><strong>#{i}</strong></td>
                    <td>{bottleneck['resource']}</td>
                    <td>{bottleneck['period']}</td>
                    <td><span class="type-badge type-{bottleneck['type']}">{bottleneck['type']}</span></td>
                    <td><strong>${bottleneck['marginal_value']:.2f}/unit</strong></td>
                    <td><span class="priority-badge {priority_class}">{bottleneck['priority']}</span></td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>

    <div class="whatif-section">
        <h2>Sensitivity Analysis</h2>
        <p style="color: #6c757d; margin-bottom: 15px;">
            How profit varies with capacity changes (showing first analyzed resource)
        </p>
    """

    # Get first sensitivity range if available
    sensitivity_ranges = whatif_results.get("sensitivity_ranges", {})
    if sensitivity_ranges:
        first_key = next(iter(sensitivity_ranges))
        sensitivity_data = sensitivity_ranges[first_key]

        html += f"""
        <div class="sensitivity-chart-container">
            <h3 style="color: #11998e; margin-bottom: 15px;">{first_key.replace('_', ' ')}</h3>
            <table class="whatif-table">
                <thead>
                    <tr>
                        <th>Capacity</th>
                        <th>Profit</th>
                        <th>vs Baseline</th>
                        <th>% Change</th>
                    </tr>
                </thead>
                <tbody>
        """

        for data_point in sensitivity_data:
            delta_class = "positive-delta" if data_point["delta"] > 0 else ("negative-delta" if data_point["delta"] < 0 else "")
            marker = " (baseline)" if abs(data_point["delta"]) < 0.01 else ""
            html += f"""
                    <tr>
                        <td>{data_point['capacity']:.0f}</td>
                        <td>${data_point['profit']:,.2f}</td>
                        <td class="{delta_class}">${data_point['delta']:+,.2f}</td>
                        <td class="{delta_class}">{data_point['delta_pct']:+.2f}%{marker}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

    html += """
    </div>

    <div class="whatif-section">
        <h2>Investment ROI Comparison</h2>
        <p style="color: #6c757d; margin-bottom: 15px;">
            Comparing different capacity expansion investment options
        </p>
        <table class="whatif-table">
            <thead>
                <tr>
                    <th>Investment Option</th>
                    <th>Amount</th>
                    <th>Profit Increase</th>
                    <th>ROI per Unit</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
    """

    investments = whatif_results.get("investment_comparison", [])
    # Sort by ROI
    sorted_investments = sorted(investments, key=lambda x: x["roi_per_unit"], reverse=True)

    for i, inv in enumerate(sorted_investments):
        recommendation = "★ BEST" if i == 0 else ("Good" if inv["roi_per_unit"] > 1.0 else "Low Priority")
        rec_class = "rec-best" if i == 0 else ("rec-good" if inv["roi_per_unit"] > 1.0 else "rec-low")

        html += f"""
                <tr>
                    <td>{inv['description']}</td>
                    <td>{inv['amount']:.0f} units</td>
                    <td>${inv['delta_profit']:,.2f}</td>
                    <td><strong>${inv['roi_per_unit']:.2f}/unit</strong></td>
                    <td><span class="rec-badge {rec_class}">{recommendation}</span></td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>

    <div class="whatif-section">
        <h2>Risk Assessment (Downside Scenarios)</h2>
        <p style="color: #6c757d; margin-bottom: 15px;">
            Impact of capacity reduction scenarios (equipment failure, supply disruption, etc.)
        </p>
        <table class="whatif-table risk-table">
            <thead>
                <tr>
                    <th>Risk Scenario</th>
                    <th>Capacity Change</th>
                    <th>Profit Loss</th>
                    <th>Loss %</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
    """

    for scenario in whatif_results.get("risk_scenarios", []):
        loss = abs(scenario["profit_loss"])
        severity = "HIGH" if loss > 1000 else ("MEDIUM" if loss > 500 else "LOW")
        severity_class = f"severity-{severity.lower()}"

        html += f"""
                <tr>
                    <td><strong>{scenario['description']}</strong></td>
                    <td>{scenario['change']:.0f} units</td>
                    <td class="risk-loss">${loss:,.2f}</td>
                    <td class="risk-loss">{scenario['loss_pct']:.2f}%</td>
                    <td><span class="severity-badge {severity_class}">⚠ {severity}</span></td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>

    <div class="whatif-section">
        <h2>Key Insights & Recommendations</h2>
        <div class="insights-grid">
    """

    # Generate insights based on data
    if bottlenecks:
        top_bottleneck = bottlenecks[0]
        html += f"""
            <div class="insight-card">
                <div class="insight-icon">🎯</div>
                <div class="insight-title">Top Bottleneck</div>
                <div class="insight-content">
                    <strong>{top_bottleneck['resource']}</strong> in {top_bottleneck['period']}
                    has marginal value of <strong>${top_bottleneck['marginal_value']:.2f}/unit</strong>.
                    Prioritize expanding this resource for maximum profit impact.
                </div>
            </div>
        """

    if investments:
        best_inv = sorted_investments[0]
        html += f"""
            <div class="insight-card">
                <div class="insight-icon">💰</div>
                <div class="insight-title">Best Investment</div>
                <div class="insight-content">
                    <strong>{best_inv['description']}</strong> offers best ROI at
                    <strong>${best_inv['roi_per_unit']:.2f}/unit</strong>,
                    with total profit increase of <strong>${best_inv['delta_profit']:,.2f}</strong>.
                </div>
            </div>
        """

    risk_scenarios = whatif_results.get("risk_scenarios", [])
    if risk_scenarios:
        worst_risk = max(risk_scenarios, key=lambda x: abs(x["profit_loss"]))
        html += f"""
            <div class="insight-card">
                <div class="insight-icon">⚠️</div>
                <div class="insight-title">Highest Risk</div>
                <div class="insight-content">
                    <strong>{worst_risk['description']}</strong> would result in
                    <strong>${abs(worst_risk['profit_loss']):,.2f}</strong> profit loss.
                    Consider mitigation strategies or contingency planning.
                </div>
            </div>
        """

    html += """
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


def generate_html_report(solution, session, whatif_results: Dict, output_path: str = "production_whatif_report.html"):
    """Generate comprehensive interactive HTML report with what-if analysis.

    Creates a modern, self-contained HTML5 + CSS dashboard with multiple views:
    - Summary dashboard with key metrics
    - Multi-period production schedule
    - Resource utilization analysis
    - Customer order fulfillment tracking
    - What-If Analysis Dashboard (NEW)

    Args:
        solution: LXSolution object from optimization
        session: SQLAlchemy Session for database access
        whatif_results: Dictionary containing what-if analysis results
        output_path: Path where HTML file will be saved

    Example:
        >>> from report_generator import generate_html_report
        >>> generate_html_report(solution, session, whatif_results, "report.html")
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution to generate report from!")
        return

    print("\n" + "=" * 80)
    print("GENERATING INTERACTIVE HTML REPORT WITH WHAT-IF ANALYSIS")
    print("=" * 80)

    # Extract data
    production_data = extract_production_data(solution, session)
    inventory_data = extract_inventory_data(solution, session)
    stats = calculate_statistics(solution, session, production_data, inventory_data)

    print(f"  Extracting production data...")
    print(f"  Calculating statistics...")

    # Generate view HTML
    summary_html = generate_summary_dashboard_html(stats, session)
    whatif_html = generate_whatif_dashboard_html(whatif_results)
    schedule_html = generate_production_schedule_html(production_data, inventory_data, session)
    resources_html = generate_resource_utilization_html(stats, session)
    orders_html = generate_order_fulfillment_html(production_data, session)

    print(f"  Generating summary dashboard...")
    print(f"  Generating what-if analysis dashboard...")
    print(f"  Generating production schedule...")
    print(f"  Generating resource utilization...")
    print(f"  Generating order fulfillment...")

    # Complete HTML document with enhanced CSS for what-if sections
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Production Planning Report - Multi-Period with What-If Analysis</title>
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

        /* What-If Analysis Styles */
        .whatif-section {{
            margin: 30px 0;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 12px;
        }}

        .whatif-section h2 {{
            color: #11998e;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }}

        .whatif-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .whatif-metric-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            text-align: center;
        }}

        .metric-label {{
            font-size: 0.9rem;
            color: #6c757d;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #11998e;
            margin: 10px 0;
        }}

        .metric-sublabel {{
            font-size: 0.85rem;
            color: #6c757d;
        }}

        .whatif-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .whatif-table th {{
            background: #11998e;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .whatif-table td {{
            padding: 12px 10px;
            border: 1px solid #dee2e6;
        }}

        .positive-delta {{
            color: #28a745;
            font-weight: 600;
        }}

        .negative-delta {{
            color: #dc3545;
            font-weight: 600;
        }}

        .type-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .type-machine {{
            background: #e3f2fd;
            color: #1976d2;
        }}

        .type-material {{
            background: #fff3e0;
            color: #f57c00;
        }}

        .priority-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .priority-high {{
            background: #ff5252;
            color: white;
        }}

        .priority-medium {{
            background: #ffa726;
            color: white;
        }}

        .priority-low {{
            background: #bdbdbd;
            color: white;
        }}

        .rec-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .rec-best {{
            background: #4caf50;
            color: white;
        }}

        .rec-good {{
            background: #8bc34a;
            color: white;
        }}

        .rec-low {{
            background: #e0e0e0;
            color: #666;
        }}

        .severity-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .severity-high {{
            background: #f44336;
            color: white;
        }}

        .severity-medium {{
            background: #ff9800;
            color: white;
        }}

        .severity-low {{
            background: #4caf50;
            color: white;
        }}

        .risk-loss {{
            color: #dc3545;
            font-weight: 600;
        }}

        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .insight-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .insight-icon {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}

        .insight-title {{
            font-weight: 700;
            color: #11998e;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }}

        .insight-content {{
            color: #6c757d;
            line-height: 1.6;
        }}

        /* Production Schedule Styles (from Step 4) */
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

        /* Resource Utilization Styles (from Step 4) */
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

        /* Order Fulfillment Styles (from Step 4) */
        .priority-section {{
            margin: 30px 0;
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
            <h1>Multi-Period Production Planning with What-If Analysis</h1>
            <p>Interactive Manufacturing Optimization Dashboard - Generated by LumiX</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('summary')">Summary Dashboard</button>
            <button class="tab" onclick="showTab('whatif')">What-If Analysis</button>
            <button class="tab" onclick="showTab('schedule')">Production Schedule</button>
            <button class="tab" onclick="showTab('resources')">Resource Utilization</button>
            <button class="tab" onclick="showTab('orders')">Customer Orders</button>
        </div>

        <div id="summary" class="tab-content active">
            <h2>Summary Dashboard</h2>
            {summary_html}
        </div>

        <div id="whatif" class="tab-content">
            <h2>What-If Analysis</h2>
            {whatif_html}
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
    print(f"  ✓ What-If Scenarios: {len(whatif_results.get('capacity_changes', [])) + len(whatif_results.get('risk_scenarios', []))}")
    print("=" * 80)
