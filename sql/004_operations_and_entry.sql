-- Approval, audit, and smart-entry tables.
create table if not exists data_entry_submissions (
  id uuid primary key default gen_random_uuid(), submission_code text unique,
  entry_type text not null, target_table text not null, payload jsonb not null default '{}'::jsonb,
  status text not null default 'submitted', submitted_by uuid,
  submitted_at timestamptz not null default now(), reviewed_by uuid,
  reviewed_at timestamptz, review_note text
);
create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(), action text not null, table_name text not null,
  record_id uuid, actor_id uuid, details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
alter table data_entry_submissions enable row level security;
alter table audit_log enable row level security;
drop policy if exists authenticated_read on data_entry_submissions;
drop policy if exists authenticated_write on data_entry_submissions;
drop policy if exists authenticated_read on audit_log;
drop policy if exists authenticated_write on audit_log;
create policy authenticated_read on data_entry_submissions for select to authenticated using (true);
create policy authenticated_write on data_entry_submissions for all to authenticated using (true) with check (true);
create policy authenticated_read on audit_log for select to authenticated using (true);
create policy authenticated_write on audit_log for insert to authenticated with check (true);

create index if not exists production_records_date_idx on production_records(production_date);
create index if not exists orders_due_date_idx on customer_orders(due_date);
create index if not exists attendance_date_idx on employee_attendance(attendance_date);
create index if not exists maintenance_status_idx on maintenance_records(status);
create index if not exists submissions_status_idx on data_entry_submissions(status);
create index if not exists inventory_material_idx on inventory(material_id);

-- Add readable codes to databases created by the earlier schema version.
alter table departments add column if not exists department_code text;
alter table employees add column if not exists employee_code text;
alter table products add column if not exists product_code text;
alter table suppliers add column if not exists supplier_code text;
alter table materials add column if not exists material_code text;
alter table production_lines add column if not exists line_code text;
alter table customer_orders add column if not exists order_code text;
alter table production_records add column if not exists production_code text;
alter table purchase_orders add column if not exists purchase_order_code text;
alter table maintenance_records add column if not exists maintenance_code text;
alter table quality_inspections add column if not exists inspection_code text;
alter table shipments add column if not exists shipment_code text;
alter table operating_costs add column if not exists cost_code text;
alter table safety_incidents add column if not exists incident_code text;

alter table products add column if not exists standard_cost numeric(14,2) not null default 0;
alter table products add column if not exists selling_price numeric(14,2) not null default 0;
alter table suppliers add column if not exists supplier_code text;
alter table suppliers add column if not exists quality_score numeric(5,2) not null default 0;
alter table suppliers add column if not exists average_lead_days numeric(8,2) not null default 0;
alter table suppliers add column if not exists active boolean not null default true;
alter table materials add column if not exists safety_stock numeric(14,3) not null default 0;
alter table materials add column if not exists unit_cost numeric(14,2) not null default 0;
alter table materials add column if not exists active boolean not null default true;
alter table machines add column if not exists next_maintenance_date date;
alter table customer_orders add column if not exists customer_id uuid references customers(id);
alter table customer_orders add column if not exists order_date date default current_date;
alter table customer_orders add column if not exists unit_price numeric(14,2) not null default 0;
alter table production_records add column if not exists recorded_by uuid;
alter table purchase_orders add column if not exists order_date date default current_date;
alter table purchase_orders add column if not exists actual_delivery_date date;
alter table purchase_orders add column if not exists unit_cost numeric(14,2) not null default 0;
alter table maintenance_records add column if not exists priority text not null default 'normal';
alter table maintenance_records add column if not exists reported_by uuid;
alter table quality_inspections add column if not exists inspected_by uuid;
alter table quality_inspections add column if not exists approval_status text not null default 'pending';
alter table shipments add column if not exists tracking_reference text;
alter table shipments add column if not exists freight_cost numeric(14,2) not null default 0;
alter table operating_costs add column if not exists product_id uuid references products(id);
alter table operating_costs add column if not exists production_line_id uuid references production_lines(id);

-- Human-readable codes for records created after the migration. The UUID remains
-- the internal primary key; the visible code is stable and short.
create or replace function factoryops_assign_code() returns trigger
language plpgsql as $$
begin
  if tg_table_name = 'departments' and new.department_code is null then new.department_code := 'DEP-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'employees' and new.employee_code is null then new.employee_code := 'EMP-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'products' and new.product_code is null then new.product_code := 'PRD-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'suppliers' and new.supplier_code is null then new.supplier_code := 'SUP-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'materials' and new.material_code is null then new.material_code := 'MAT-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'production_lines' and new.line_code is null then new.line_code := 'LINE-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'customer_orders' and new.order_code is null then new.order_code := 'ORD-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'production_records' and new.production_code is null then new.production_code := 'PROD-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'purchase_orders' and new.purchase_order_code is null then new.purchase_order_code := 'PO-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'maintenance_records' and new.maintenance_code is null then new.maintenance_code := 'MNT-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'quality_inspections' and new.inspection_code is null then new.inspection_code := 'QIN-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'shipments' and new.shipment_code is null then new.shipment_code := 'SHP-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'operating_costs' and new.cost_code is null then new.cost_code := 'CST-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'safety_incidents' and new.incident_code is null then new.incident_code := 'INC-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'inventory_movements' and new.movement_code is null then new.movement_code := 'MOV-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  if tg_table_name = 'data_entry_submissions' and new.submission_code is null then new.submission_code := 'SUB-' || upper(substr(replace(new.id::text, '-', ''), 1, 6)); end if;
  return new;
end $$;

drop trigger if exists factoryops_codes on departments;
create trigger factoryops_codes before insert on departments for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on employees;
create trigger factoryops_codes before insert on employees for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on products;
create trigger factoryops_codes before insert on products for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on suppliers;
create trigger factoryops_codes before insert on suppliers for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on materials;
create trigger factoryops_codes before insert on materials for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on production_lines;
create trigger factoryops_codes before insert on production_lines for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on customer_orders;
create trigger factoryops_codes before insert on customer_orders for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on production_records;
create trigger factoryops_codes before insert on production_records for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on purchase_orders;
create trigger factoryops_codes before insert on purchase_orders for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on maintenance_records;
create trigger factoryops_codes before insert on maintenance_records for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on quality_inspections;
create trigger factoryops_codes before insert on quality_inspections for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on shipments;
create trigger factoryops_codes before insert on shipments for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on operating_costs;
create trigger factoryops_codes before insert on operating_costs for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on safety_incidents;
create trigger factoryops_codes before insert on safety_incidents for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on inventory_movements;
create trigger factoryops_codes before insert on inventory_movements for each row execute function factoryops_assign_code();
drop trigger if exists factoryops_codes on data_entry_submissions;
create trigger factoryops_codes before insert on data_entry_submissions for each row execute function factoryops_assign_code();
