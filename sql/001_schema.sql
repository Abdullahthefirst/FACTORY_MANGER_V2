-- FactoryOps core schema. Run in Supabase SQL Editor.
-- The migration is rerunnable and retains UUID relationships.

create extension if not exists "pgcrypto";

create table if not exists departments (
  id uuid primary key default gen_random_uuid(), department_code text unique,
  name text not null unique, created_at timestamptz not null default now()
);
create table if not exists employees (
  id uuid primary key default gen_random_uuid(), employee_code text unique,
  full_name text not null, role text, department_id uuid references departments(id),
  skill_level text, active boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists products (
  id uuid primary key default gen_random_uuid(), product_code text unique,
  name text not null unique, unit text not null default 'units',
  standard_cost numeric(14,2) not null default 0,
  selling_price numeric(14,2) not null default 0, active boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists customers (
  id uuid primary key default gen_random_uuid(), customer_code text unique,
  name text not null unique, contact_person text, email text, phone text,
  active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists suppliers (
  id uuid primary key default gen_random_uuid(), supplier_code text unique,
  name text not null unique, contact_person text, phone text, email text,
  reliability_score numeric(5,2) not null default 0,
  quality_score numeric(5,2) not null default 0,
  average_lead_days numeric(8,2) not null default 0,
  active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists materials (
  id uuid primary key default gen_random_uuid(), material_code text unique,
  name text not null unique, unit text not null default 'kg',
  reorder_level numeric(14,3) not null default 0,
  safety_stock numeric(14,3) not null default 0,
  supplier_id uuid references suppliers(id), unit_cost numeric(14,2) not null default 0,
  active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists product_material_requirements (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references products(id) on delete cascade,
  material_id uuid not null references materials(id), quantity_per_unit numeric(14,5) not null default 0,
  unique(product_id, material_id)
);
create table if not exists production_lines (
  id uuid primary key default gen_random_uuid(), line_code text unique,
  name text not null unique, department_id uuid references departments(id),
  capacity_per_shift numeric(14,2) not null default 0, active boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists machines (
  id uuid primary key default gen_random_uuid(), machine_code text unique, name text not null,
  production_line_id uuid references production_lines(id), status text not null default 'operational',
  last_maintenance_date date, next_maintenance_date date, created_at timestamptz not null default now()
);
create table if not exists shifts (
  id uuid primary key default gen_random_uuid(), name text not null unique,
  start_time time, end_time time, active boolean not null default true
);
create table if not exists customer_orders (
  id uuid primary key default gen_random_uuid(), order_code text unique,
  customer_id uuid references customers(id), customer_name text, product_id uuid references products(id),
  quantity numeric(14,2) not null default 0, order_date date not null default current_date,
  due_date date, priority text not null default 'normal', status text not null default 'pending',
  unit_price numeric(14,2) not null default 0, created_at timestamptz not null default now()
);
create table if not exists production_plans (
  id uuid primary key default gen_random_uuid(), plan_code text unique, plan_date date not null,
  shift_id uuid references shifts(id), production_line_id uuid references production_lines(id),
  product_id uuid references products(id), planned_quantity numeric(14,2) not null default 0,
  status text not null default 'planned', notes text, created_at timestamptz not null default now()
);
create table if not exists production_records (
  id uuid primary key default gen_random_uuid(), production_code text unique,
  production_date date not null, shift_id uuid references shifts(id),
  production_line_id uuid references production_lines(id), product_id uuid references products(id),
  planned_quantity numeric(14,2) not null default 0, actual_quantity numeric(14,2) not null default 0,
  rejected_quantity numeric(14,2) not null default 0, downtime_minutes numeric(14,2) not null default 0,
  downtime_reason text, status text not null default 'completed', recorded_by uuid references employees(id),
  created_at timestamptz not null default now()
);
create table if not exists inventory (
  id uuid primary key default gen_random_uuid(), material_id uuid not null references materials(id),
  quantity numeric(14,3) not null default 0, warehouse_location text not null default 'Main warehouse',
  last_updated timestamptz not null default now(), unique(material_id, warehouse_location)
);
create table if not exists purchase_orders (
  id uuid primary key default gen_random_uuid(), purchase_order_code text unique,
  material_id uuid references materials(id), supplier_id uuid references suppliers(id),
  ordered_quantity numeric(14,3) not null default 0, received_quantity numeric(14,3) not null default 0,
  order_date date not null default current_date, expected_date date, actual_delivery_date date,
  status text not null default 'ordered', unit_cost numeric(14,2) not null default 0,
  notes text, created_at timestamptz not null default now()
);
create table if not exists inventory_movements (
  id uuid primary key default gen_random_uuid(), movement_code text unique,
  material_id uuid not null references materials(id), movement_type text not null,
  quantity numeric(14,3) not null default 0, movement_date date not null default current_date,
  warehouse_location text not null default 'Main warehouse', reference text, recorded_by uuid,
  created_at timestamptz not null default now()
);
create table if not exists maintenance_records (
  id uuid primary key default gen_random_uuid(), maintenance_code text unique,
  machine_id uuid references machines(id), issue_type text, description text,
  downtime_minutes numeric(14,2) not null default 0, status text not null default 'open',
  priority text not null default 'normal', reported_by uuid, reported_at timestamptz not null default now(),
  resolved_at timestamptz, resolution_notes text
);
create table if not exists quality_inspections (
  id uuid primary key default gen_random_uuid(), inspection_code text unique,
  production_record_id uuid references production_records(id), inspected_quantity numeric(14,2) not null default 0,
  rejected_quantity numeric(14,2) not null default 0, defect_type text, notes text, inspected_by uuid,
  inspection_date date not null default current_date, approval_status text not null default 'pending'
);
create table if not exists customer_complaints (
  id uuid primary key default gen_random_uuid(), complaint_code text unique,
  customer_id uuid references customers(id), order_id uuid references customer_orders(id),
  product_id uuid references products(id), complaint_date date not null default current_date,
  complaint_type text, description text, status text not null default 'open',
  root_cause text, corrective_action text
);
create table if not exists employee_attendance (
  id uuid primary key default gen_random_uuid(), employee_id uuid references employees(id),
  attendance_date date not null default current_date, status text not null default 'present',
  shift_id uuid references shifts(id), overtime_hours numeric(8,2) not null default 0, notes text,
  unique(employee_id, attendance_date)
);
create table if not exists shipments (
  id uuid primary key default gen_random_uuid(), shipment_code text unique,
  order_id uuid references customer_orders(id), shipment_date date, expected_delivery_date date,
  actual_delivery_date date, status text not null default 'pending', carrier text,
  tracking_reference text, freight_cost numeric(14,2) not null default 0, notes text
);
create table if not exists operating_costs (
  id uuid primary key default gen_random_uuid(), cost_code text unique, cost_date date not null default current_date,
  category text not null, amount numeric(14,2) not null default 0, product_id uuid references products(id),
  production_line_id uuid references production_lines(id), description text
);
create table if not exists safety_incidents (
  id uuid primary key default gen_random_uuid(), incident_code text unique,
  incident_date date not null default current_date, incident_type text not null,
  severity text not null default 'medium', status text not null default 'open', description text,
  corrective_action text, closed_at timestamptz
);
create table if not exists factory_alerts (
  id uuid primary key default gen_random_uuid(), alert_type text not null, severity text not null default 'medium',
  title text not null, description text, related_table text, related_record_id uuid,
  resolved boolean not null default false, created_at timestamptz not null default now(), resolved_at timestamptz
);
