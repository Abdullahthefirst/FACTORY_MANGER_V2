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
alter table if exists departments add column if not exists department_code text;
alter table if exists employees add column if not exists employee_code text;
alter table if exists products add column if not exists product_code text;
alter table if exists customers add column if not exists customer_code text;
alter table if exists suppliers add column if not exists supplier_code text;
alter table if exists materials add column if not exists material_code text;
alter table if exists production_lines add column if not exists line_code text;
alter table if exists machines add column if not exists machine_code text;
alter table if exists customer_orders add column if not exists order_code text;
alter table if exists production_plans add column if not exists plan_code text;
alter table if exists production_records add column if not exists production_code text;
alter table if exists purchase_orders add column if not exists purchase_order_code text;
alter table if exists inventory_movements add column if not exists movement_code text;
alter table if exists maintenance_records add column if not exists maintenance_code text;
alter table if exists quality_inspections add column if not exists inspection_code text;
alter table if exists customer_complaints add column if not exists complaint_code text;
alter table if exists shipments add column if not exists shipment_code text;
alter table if exists operating_costs add column if not exists cost_code text;
alter table if exists safety_incidents add column if not exists incident_code text;
alter table if exists data_entry_submissions add column if not exists submission_code text;

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
create or replace function public.factoryops_assign_code()
returns trigger
language plpgsql
as $$
declare
  code_column text := tg_argv[0];
  code_prefix text := tg_argv[1];
  row_data jsonb;
  generated_code text;
begin
  row_data := to_jsonb(new);

  -- Ignore a trigger configured for a column that is absent from this row type.
  if not (row_data ? code_column) then
    return new;
  end if;

  -- Preserve a code supplied by the caller.
  if nullif(btrim(row_data ->> code_column), '') is not null then
    return new;
  end if;

  generated_code :=
    code_prefix ||
    upper(substr(replace(new.id::text, '-', ''), 1, 6));

  row_data := jsonb_set(
    row_data,
    array[code_column],
    to_jsonb(generated_code),
    true
  );

  new := jsonb_populate_record(new, row_data);

  return new;
end;
$$;

do $$
declare
  item record;
begin
  for item in
    select *
    from (
      values
        ('departments',            'department_code',       'DEP-'),
        ('employees',              'employee_code',         'EMP-'),
        ('products',               'product_code',          'PRD-'),
        ('customers',              'customer_code',         'CUS-'),
        ('suppliers',              'supplier_code',         'SUP-'),
        ('materials',              'material_code',         'MAT-'),
        ('production_lines',       'line_code',             'LINE-'),
        ('machines',               'machine_code',          'MCH-'),
        ('customer_orders',        'order_code',            'ORD-'),
        ('production_plans',       'plan_code',             'PLAN-'),
        ('production_records',     'production_code',       'PROD-'),
        ('purchase_orders',        'purchase_order_code',   'PO-'),
        ('inventory_movements',    'movement_code',         'MOV-'),
        ('maintenance_records',    'maintenance_code',      'MNT-'),
        ('quality_inspections',    'inspection_code',       'QIN-'),
        ('customer_complaints',    'complaint_code',        'CMP-'),
        ('shipments',              'shipment_code',         'SHP-'),
        ('operating_costs',        'cost_code',             'CST-'),
        ('safety_incidents',       'incident_code',         'INC-'),
        ('data_entry_submissions', 'submission_code',       'SUB-')
    ) as code_tables(table_name, column_name, code_prefix)
  loop
    if to_regclass('public.' || quote_ident(item.table_name)) is not null then
      execute format(
        'drop trigger if exists factoryops_codes on public.%I',
        item.table_name
      );

      execute format(
        'create trigger factoryops_codes
         before insert on public.%I
         for each row
         execute function public.factoryops_assign_code(%L, %L)',
        item.table_name,
        item.column_name,
        item.code_prefix
      );

      -- Fill codes missing from existing records.
      execute format(
        'update public.%I
         set %I = %L || upper(substr(replace(id::text, ''-'', ''''), 1, 6))
         where nullif(btrim(%I), '''') is null',
        item.table_name,
        item.column_name,
        item.code_prefix,
        item.column_name
      );
    end if;
  end loop;
end;
$$;
