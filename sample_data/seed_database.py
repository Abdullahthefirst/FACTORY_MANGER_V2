"""Repeatable sample-data loader for FactoryOps.

The manager app exposes this loader as an authenticated button, so sample data
can be loaded through Streamlit Cloud without a local package installation.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def ident(code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"factoryops-sample:{code}"))


def upsert(client: Any, table: str, rows: list[dict[str, Any]], conflict: str) -> list[dict[str, Any]]:
    if not rows:
        return []
    response = client.table(table).upsert(rows, on_conflict=conflict).execute()
    return response.data or rows


def load_sample_database(client: Any) -> dict[str, int]:
    """Insert linked master and operational data; existing sample codes update."""
    today = date.today()

    departments = [
        {"id": ident("DEP-DYE"), "department_code": "DEP-001", "name": "Dyeing"},
        {"id": ident("DEP-SPIN"), "department_code": "DEP-002", "name": "Spinning"},
        {"id": ident("DEP-WEAV"), "department_code": "DEP-003", "name": "Weaving"},
        {"id": ident("DEP-FIN"), "department_code": "DEP-004", "name": "Finishing"},
    ]
    upsert(client, "departments", departments, "department_code")

    products = [
        {"id": ident("PRD-DYED"), "product_code": "PRD-001", "name": "Dyed Fabric", "unit": "meters", "standard_cost": 175, "selling_price": 240},
        {"id": ident("PRD-YARN"), "product_code": "PRD-002", "name": "Cotton Yarn", "unit": "kg", "standard_cost": 420, "selling_price": 560},
        {"id": ident("PRD-WOVEN"), "product_code": "PRD-003", "name": "Cotton Fabric", "unit": "meters", "standard_cost": 210, "selling_price": 295},
        {"id": ident("PRD-POLY"), "product_code": "PRD-004", "name": "Polyester Blend", "unit": "meters", "standard_cost": 195, "selling_price": 275},
        {"id": ident("PRD-FIN"), "product_code": "PRD-005", "name": "Finished Roll", "unit": "rolls", "standard_cost": 1350, "selling_price": 1750},
    ]
    upsert(client, "products", products, "product_code")

    suppliers = [
        {"id": ident("SUP-COT"), "supplier_code": "SUP-001", "name": "Cotton Source Ltd", "reliability_score": 94, "quality_score": 96, "average_lead_days": 5},
        {"id": ident("SUP-FIB"), "supplier_code": "SUP-002", "name": "National Fiber Traders", "reliability_score": 72, "quality_score": 88, "average_lead_days": 10},
        {"id": ident("SUP-CHEM"), "supplier_code": "SUP-003", "name": "ColorChem Industries", "reliability_score": 81, "quality_score": 90, "average_lead_days": 8},
        {"id": ident("SUP-PKG"), "supplier_code": "SUP-004", "name": "PackRight Supplies", "reliability_score": 97, "quality_score": 95, "average_lead_days": 3},
    ]
    upsert(client, "suppliers", suppliers, "supplier_code")

    materials = [
        {"id": ident("MAT-COT"), "material_code": "MAT-001", "name": "Raw Cotton", "unit": "kg", "reorder_level": 1000, "safety_stock": 500, "supplier_id": ident("SUP-COT"), "unit_cost": 310},
        {"id": ident("MAT-POL"), "material_code": "MAT-002", "name": "Polyester Fiber", "unit": "kg", "reorder_level": 800, "safety_stock": 300, "supplier_id": ident("SUP-FIB"), "unit_cost": 280},
        {"id": ident("MAT-DYE"), "material_code": "MAT-003", "name": "Blue Dye", "unit": "kg", "reorder_level": 100, "safety_stock": 40, "supplier_id": ident("SUP-CHEM"), "unit_cost": 1250},
        {"id": ident("MAT-PKG"), "material_code": "MAT-004", "name": "Packaging Rolls", "unit": "units", "reorder_level": 200, "safety_stock": 100, "supplier_id": ident("SUP-PKG"), "unit_cost": 75},
        {"id": ident("MAT-CHEM"), "material_code": "MAT-005", "name": "Finishing Chemical", "unit": "kg", "reorder_level": 150, "safety_stock": 60, "supplier_id": ident("SUP-CHEM"), "unit_cost": 690},
    ]
    upsert(client, "materials", materials, "material_code")

    lines = [
        {"id": ident("LINE-DYE"), "line_code": "LINE-001", "name": "Dyeing Line 1", "department_id": ident("DEP-DYE"), "capacity_per_shift": 11000},
        {"id": ident("LINE-SPIN"), "line_code": "LINE-002", "name": "Spinning Line 1", "department_id": ident("DEP-SPIN"), "capacity_per_shift": 9000},
        {"id": ident("LINE-WEAV"), "line_code": "LINE-003", "name": "Weaving Line 1", "department_id": ident("DEP-WEAV"), "capacity_per_shift": 10000},
    ]
    upsert(client, "production_lines", lines, "line_code")

    machines = [
        {"id": ident("MCH-DYE"), "machine_code": "MCH-001", "name": "Dyeing Machine 1", "production_line_id": ident("LINE-DYE"), "status": "operational", "last_maintenance_date": (today - timedelta(days=8)).isoformat(), "next_maintenance_date": (today + timedelta(days=22)).isoformat()},
        {"id": ident("MCH-SP1"), "machine_code": "MCH-002", "name": "Spinning Machine 1", "production_line_id": ident("LINE-SPIN"), "status": "operational", "last_maintenance_date": (today - timedelta(days=12)).isoformat(), "next_maintenance_date": (today + timedelta(days=18)).isoformat()},
        {"id": ident("MCH-SP2"), "machine_code": "MCH-003", "name": "Spinning Machine 2", "production_line_id": ident("LINE-SPIN"), "status": "maintenance", "last_maintenance_date": (today - timedelta(days=60)).isoformat(), "next_maintenance_date": today.isoformat()},
        {"id": ident("MCH-WV"), "machine_code": "MCH-004", "name": "Weaving Machine 1", "production_line_id": ident("LINE-WEAV"), "status": "operational", "last_maintenance_date": (today - timedelta(days=5)).isoformat(), "next_maintenance_date": (today + timedelta(days=25)).isoformat()},
        {"id": ident("MCH-FIN"), "machine_code": "MCH-005", "name": "Finishing Machine 1", "production_line_id": ident("LINE-WEAV"), "status": "operational", "last_maintenance_date": (today - timedelta(days=15)).isoformat(), "next_maintenance_date": (today + timedelta(days=15)).isoformat()},
    ]
    upsert(client, "machines", machines, "machine_code")

    shifts = [
        {"id": ident("SHIFT-A"), "name": "Shift A", "start_time": "06:00", "end_time": "14:00"},
        {"id": ident("SHIFT-B"), "name": "Shift B", "start_time": "14:00", "end_time": "22:00"},
        {"id": ident("SHIFT-C"), "name": "Shift C", "start_time": "22:00", "end_time": "06:00"},
    ]
    upsert(client, "shifts", shifts, "name")

    employees = [
        {"id": ident("EMP-001"), "employee_code": "EMP-001", "full_name": "Ayesha Khan", "role": "Dyeing Supervisor", "department_id": ident("DEP-DYE"), "skill_level": "Expert"},
        {"id": ident("EMP-002"), "employee_code": "EMP-002", "full_name": "Bilal Ahmed", "role": "Spinning Operator", "department_id": ident("DEP-SPIN"), "skill_level": "Advanced"},
        {"id": ident("EMP-003"), "employee_code": "EMP-003", "full_name": "Hassan Raza", "role": "Weaving Operator", "department_id": ident("DEP-WEAV"), "skill_level": "Advanced"},
        {"id": ident("EMP-004"), "employee_code": "EMP-004", "full_name": "Maryam Iqbal", "role": "Quality Inspector", "department_id": ident("DEP-FIN"), "skill_level": "Expert"},
        {"id": ident("EMP-005"), "employee_code": "EMP-005", "full_name": "Omar Farooq", "role": "Maintenance Technician", "department_id": ident("DEP-SPIN"), "skill_level": "Expert"},
        {"id": ident("EMP-006"), "employee_code": "EMP-006", "full_name": "Sana Malik", "role": "Production Planner", "department_id": ident("DEP-DYE"), "skill_level": "Advanced"},
        {"id": ident("EMP-007"), "employee_code": "EMP-007", "full_name": "Usman Tariq", "role": "Line Operator", "department_id": ident("DEP-WEAV"), "skill_level": "Intermediate"},
        {"id": ident("EMP-008"), "employee_code": "EMP-008", "full_name": "Zainab Shah", "role": "Warehouse Coordinator", "department_id": ident("DEP-FIN"), "skill_level": "Advanced"},
    ]
    upsert(client, "employees", employees, "employee_code")

    customers = [
        {"id": ident("CUS-001"), "customer_code": "CUS-001", "name": "Metro Textiles"},
        {"id": ident("CUS-002"), "customer_code": "CUS-002", "name": "Eastern Apparel"},
        {"id": ident("CUS-003"), "customer_code": "CUS-003", "name": "Lahore Garments"},
        {"id": ident("CUS-004"), "customer_code": "CUS-004", "name": "Export House"},
    ]
    upsert(client, "customers", customers, "customer_code")

    orders = [
        {"id": ident("ORD-001"), "order_code": "ORD-001", "customer_id": ident("CUS-001"), "customer_name": "Metro Textiles", "product_id": ident("PRD-DYED"), "quantity": 18000, "order_date": (today - timedelta(days=7)).isoformat(), "due_date": (today + timedelta(days=4)).isoformat(), "priority": "urgent", "status": "in production", "unit_price": 240},
        {"id": ident("ORD-002"), "order_code": "ORD-002", "customer_id": ident("CUS-002"), "customer_name": "Eastern Apparel", "product_id": ident("PRD-YARN"), "quantity": 12000, "order_date": (today - timedelta(days=12)).isoformat(), "due_date": (today - timedelta(days=1)).isoformat(), "priority": "high", "status": "delayed", "unit_price": 560},
        {"id": ident("ORD-003"), "order_code": "ORD-003", "customer_id": ident("CUS-003"), "customer_name": "Lahore Garments", "product_id": ident("PRD-WOVEN"), "quantity": 15000, "order_date": (today - timedelta(days=4)).isoformat(), "due_date": (today + timedelta(days=10)).isoformat(), "priority": "normal", "status": "pending", "unit_price": 295},
        {"id": ident("ORD-004"), "order_code": "ORD-004", "customer_id": ident("CUS-004"), "customer_name": "Export House", "product_id": ident("PRD-POLY"), "quantity": 9000, "order_date": (today - timedelta(days=2)).isoformat(), "due_date": (today + timedelta(days=14)).isoformat(), "priority": "normal", "status": "pending", "unit_price": 275},
        {"id": ident("ORD-005"), "order_code": "ORD-005", "customer_id": ident("CUS-001"), "customer_name": "Metro Textiles", "product_id": ident("PRD-FIN"), "quantity": 600, "order_date": (today - timedelta(days=20)).isoformat(), "due_date": (today + timedelta(days=2)).isoformat(), "priority": "high", "status": "in production", "unit_price": 1750},
        {"id": ident("ORD-006"), "order_code": "ORD-006", "customer_id": ident("CUS-002"), "customer_name": "Eastern Apparel", "product_id": ident("PRD-YARN"), "quantity": 8000, "order_date": today.isoformat(), "due_date": (today + timedelta(days=21)).isoformat(), "priority": "normal", "status": "pending", "unit_price": 560},
    ]
    upsert(client, "customer_orders", orders, "order_code")

    plans = []
    for index in range(6):
        plans.append({
            "id": ident(f"PLAN-{index + 1:03d}"), "plan_code": f"PLAN-{index + 1:03d}",
            "plan_date": (today + timedelta(days=index - 1)).isoformat(),
            "shift_id": [ident("SHIFT-A"), ident("SHIFT-B"), ident("SHIFT-C")][index % 3],
            "production_line_id": [ident("LINE-DYE"), ident("LINE-SPIN"), ident("LINE-WEAV")][index % 3],
            "product_id": [ident("PRD-DYED"), ident("PRD-YARN"), ident("PRD-WOVEN")][index % 3],
            "planned_quantity": [10500, 8200, 9200, 10800, 7800, 9600][index],
            "status": "planned" if index >= 2 else "completed",
        })
    upsert(client, "production_plans", plans, "plan_code")

    production = []
    daily_values = [(10400, 10100, 110), (10800, 10650, 80), (9800, 9100, 260), (11200, 10950, 70), (9000, 8350, 310), (10500, 10200, 140), (8700, 7900, 420)]
    for index, (planned, actual, downtime) in enumerate(daily_values):
        for line_index, line in enumerate(["LINE-DYE", "LINE-SPIN", "LINE-WEAV"]):
            code = f"PROD-{index * 3 + line_index + 1:03d}"
            production.append({
                "id": ident(code), "production_code": code,
                "production_date": (today - timedelta(days=6 - index)).isoformat(),
                "shift_id": [ident("SHIFT-A"), ident("SHIFT-B"), ident("SHIFT-C")][line_index],
                "production_line_id": ident(line),
                "product_id": [ident("PRD-DYED"), ident("PRD-YARN"), ident("PRD-WOVEN")][line_index],
                "planned_quantity": planned // 3,
                "actual_quantity": max(actual // 3 - (line_index * 30), 0),
                "rejected_quantity": [90, 40, 140][line_index] if index in [2, 4, 6] else [25, 12, 35][line_index],
                "downtime_minutes": downtime // 3 + line_index * 10,
                "downtime_reason": "Spinning Machine 2 maintenance" if index == 6 and line_index == 1 else None,
                "status": "completed",
                "recorded_by": [ident("EMP-001"), ident("EMP-002"), ident("EMP-003")][line_index],
            })
    upsert(client, "production_records", production, "production_code")

    inventory_rows = [
        {"id": ident("INV-MAT-COT"), "material_id": ident("MAT-COT"), "quantity": 2500, "warehouse_location": "Main warehouse"},
        {"id": ident("INV-MAT-POL"), "material_id": ident("MAT-POL"), "quantity": 600, "warehouse_location": "Main warehouse"},
        {"id": ident("INV-MAT-DYE"), "material_id": ident("MAT-DYE"), "quantity": 75, "warehouse_location": "Chemical store"},
        {"id": ident("INV-MAT-PKG"), "material_id": ident("MAT-PKG"), "quantity": 450, "warehouse_location": "Packaging store"},
        {"id": ident("INV-MAT-CHEM"), "material_id": ident("MAT-CHEM"), "quantity": 190, "warehouse_location": "Chemical store"},
    ]
    upsert(client, "inventory", inventory_rows, "material_id,warehouse_location")

    purchase_orders = [
        {"id": ident("PO-001"), "purchase_order_code": "PO-001", "material_id": ident("MAT-POL"), "supplier_id": ident("SUP-FIB"), "ordered_quantity": 1500, "received_quantity": 0, "order_date": (today - timedelta(days=8)).isoformat(), "expected_date": (today - timedelta(days=1)).isoformat(), "status": "delayed", "unit_cost": 280},
        {"id": ident("PO-002"), "purchase_order_code": "PO-002", "material_id": ident("MAT-DYE"), "supplier_id": ident("SUP-CHEM"), "ordered_quantity": 300, "received_quantity": 100, "order_date": (today - timedelta(days=4)).isoformat(), "expected_date": (today + timedelta(days=3)).isoformat(), "status": "ordered", "unit_cost": 1250},
        {"id": ident("PO-003"), "purchase_order_code": "PO-003", "material_id": ident("MAT-COT"), "supplier_id": ident("SUP-COT"), "ordered_quantity": 3000, "received_quantity": 3000, "order_date": (today - timedelta(days=15)).isoformat(), "expected_date": (today - timedelta(days=7)).isoformat(), "actual_delivery_date": (today - timedelta(days=7)).isoformat(), "status": "received", "unit_cost": 310},
        {"id": ident("PO-004"), "purchase_order_code": "PO-004", "material_id": ident("MAT-PKG"), "supplier_id": ident("SUP-PKG"), "ordered_quantity": 700, "received_quantity": 0, "order_date": (today - timedelta(days=1)).isoformat(), "expected_date": (today + timedelta(days=2)).isoformat(), "status": "ordered", "unit_cost": 75},
    ]
    upsert(client, "purchase_orders", purchase_orders, "purchase_order_code")

    movements = []
    for index in range(10):
        code = f"MOV-{index + 1:03d}"
        movements.append({
            "id": ident(code), "movement_code": code, "material_id": [ident("MAT-COT"), ident("MAT-POL"), ident("MAT-DYE")][index % 3],
            "movement_type": "receipt" if index % 3 == 0 else "consumption",
            "quantity": [500, 220, 40][index % 3], "movement_date": (today - timedelta(days=index)).isoformat(),
            "warehouse_location": "Main warehouse", "reference": "Sample production movement", "recorded_by": ident("EMP-008"),
        })
    upsert(client, "inventory_movements", movements, "movement_code")

    maintenance = [
        {"id": ident("MNT-001"), "maintenance_code": "MNT-001", "machine_id": ident("MCH-WV"), "issue_type": "Preventive maintenance", "description": "Scheduled belt and bearing inspection completed.", "downtime_minutes": 45, "status": "resolved", "priority": "normal", "reported_at": (today - timedelta(days=2)).isoformat(), "resolved_at": (today - timedelta(days=2)).isoformat()},
        {"id": ident("MNT-002"), "maintenance_code": "MNT-002", "machine_id": ident("MCH-SP2"), "issue_type": "Breakdown", "description": "Unplanned spindle vibration; technician assigned.", "downtime_minutes": 180, "status": "open", "priority": "critical", "reported_at": today.isoformat()},
        {"id": ident("MNT-003"), "maintenance_code": "MNT-003", "machine_id": ident("MCH-DYE"), "issue_type": "Inspection", "description": "Temperature sensor checked.", "downtime_minutes": 0, "status": "resolved", "priority": "normal", "reported_at": (today - timedelta(days=5)).isoformat(), "resolved_at": (today - timedelta(days=5)).isoformat()},
    ]
    upsert(client, "maintenance_records", maintenance, "maintenance_code")

    inspections = []
    for index in range(8):
        code = f"QIN-{index + 1:03d}"
        inspections.append({
            "id": ident(code), "inspection_code": code, "production_record_id": ident(f"PROD-{index + 1:03d}"),
            "inspected_quantity": 3000, "rejected_quantity": 180 if index in [2, 6] else 45,
            "defect_type": "Color variation" if index in [2, 6] else "Surface", "notes": "Sample inspection record.",
            "inspected_by": ident("EMP-004"), "inspection_date": (today - timedelta(days=index % 6)).isoformat(),
        })
    upsert(client, "quality_inspections", inspections, "inspection_code")

    complaints = [
        {"id": ident("CMP-001"), "complaint_code": "CMP-001", "customer_id": ident("CUS-002"), "order_id": ident("ORD-002"), "product_id": ident("PRD-YARN"), "complaint_date": (today - timedelta(days=3)).isoformat(), "complaint_type": "Late delivery", "description": "Customer requested updated delivery commitment.", "status": "open"},
        {"id": ident("CMP-002"), "complaint_code": "CMP-002", "customer_id": ident("CUS-001"), "order_id": ident("ORD-001"), "product_id": ident("PRD-DYED"), "complaint_date": (today - timedelta(days=5)).isoformat(), "complaint_type": "Color variation", "description": "Small batch requires quality review.", "status": "investigating"},
    ]
    upsert(client, "customer_complaints", complaints, "complaint_code")

    attendance = []
    statuses = ["present", "present", "late", "present", "absent", "leave", "present", "present"]
    for index, status in enumerate(statuses):
        attendance.append({
            "id": ident(f"ATT-{today.isoformat()}-{index + 1}"), "employee_id": ident(f"EMP-{index + 1:03d}"),
            "attendance_date": today.isoformat(), "status": status,
            "shift_id": [ident("SHIFT-A"), ident("SHIFT-B"), ident("SHIFT-C")][index % 3],
            "overtime_hours": 2 if status in ["present", "late"] and index % 2 == 0 else 0,
        })
    upsert(client, "employee_attendance", attendance, "employee_id,attendance_date")

    shipments = [
        {"id": ident("SHP-001"), "shipment_code": "SHP-001", "order_id": ident("ORD-001"), "shipment_date": today.isoformat(), "expected_delivery_date": (today + timedelta(days=4)).isoformat(), "status": "in transit", "carrier": "TCS Freight", "tracking_reference": "TRK-001", "freight_cost": 45000},
        {"id": ident("SHP-002"), "shipment_code": "SHP-002", "order_id": ident("ORD-002"), "shipment_date": (today - timedelta(days=3)).isoformat(), "expected_delivery_date": (today - timedelta(days=1)).isoformat(), "status": "delayed", "carrier": "BlueLine Logistics", "tracking_reference": "TRK-002", "freight_cost": 38000},
        {"id": ident("SHP-003"), "shipment_code": "SHP-003", "order_id": ident("ORD-005"), "shipment_date": today.isoformat(), "expected_delivery_date": (today + timedelta(days=2)).isoformat(), "status": "pending", "carrier": "Metro Cargo", "tracking_reference": "TRK-003", "freight_cost": 22000},
    ]
    upsert(client, "shipments", shipments, "shipment_code")

    costs = []
    for index, category in enumerate(["Materials", "Labor", "Energy", "Maintenance", "Freight", "Materials", "Labor", "Energy"]):
        code = f"CST-{index + 1:03d}"
        costs.append({
            "id": ident(code), "cost_code": code, "cost_date": (today - timedelta(days=index)).isoformat(),
            "category": category, "amount": [120000, 65000, 43000, 18000, 12000, 98000, 62000, 47000][index],
            "description": "Sample operating-cost entry.",
        })
    upsert(client, "operating_costs", costs, "cost_code")

    incidents = [
        {"id": ident("INC-001"), "incident_code": "INC-001", "incident_date": (today - timedelta(days=1)).isoformat(), "incident_type": "Near miss", "severity": "medium", "status": "open", "description": "Material trolley entered a marked walkway."},
        {"id": ident("INC-002"), "incident_code": "INC-002", "incident_date": (today - timedelta(days=6)).isoformat(), "incident_type": "Equipment guard", "severity": "high", "status": "investigating", "description": "Guard inspection required on spinning equipment."},
        {"id": ident("INC-003"), "incident_code": "INC-003", "incident_date": (today - timedelta(days=14)).isoformat(), "incident_type": "PPE observation", "severity": "low", "status": "resolved", "description": "PPE reminder completed with shift team."},
    ]
    upsert(client, "safety_incidents", incidents, "incident_code")

    alerts = [
        {"id": ident("ALT-001"), "alert_type": "inventory", "severity": "high", "title": "Blue Dye below reorder level", "description": "Inventory is 25 units below the reorder point.", "related_table": "inventory", "related_record_id": ident("INV-MAT-DYE"), "resolved": False},
        {"id": ident("ALT-002"), "alert_type": "maintenance", "severity": "critical", "title": "Spinning Machine 2 requires attention", "description": "Open breakdown with 180 minutes of downtime.", "related_table": "machines", "related_record_id": ident("MCH-SP2"), "resolved": False},
        {"id": ident("ALT-003"), "alert_type": "order", "severity": "high", "title": "Order ORD-002 is delayed", "description": "The committed due date has passed.", "related_table": "customer_orders", "related_record_id": ident("ORD-002"), "resolved": False},
    ]
    upsert(client, "factory_alerts", alerts, "id")

    return {
        "departments": len(departments), "employees": len(employees), "products": len(products),
        "suppliers": len(suppliers), "materials": len(materials), "orders": len(orders),
        "production_records": len(production), "inventory": len(inventory_rows),
        "purchase_orders": len(purchase_orders), "maintenance_records": len(maintenance),
        "quality_inspections": len(inspections), "attendance": len(attendance),
        "shipments": len(shipments), "costs": len(costs), "safety_incidents": len(incidents),
    }
