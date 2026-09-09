-- Authenticated-user RLS for the manager and data-entry apps.
-- Add role/department claims before exposing this to untrusted users.
do $$
declare t text;
begin
  foreach t in array array[
    'departments','employees','products','customers','suppliers','materials',
    'product_material_requirements','production_lines','machines','shifts',
    'customer_orders','production_plans','production_records','inventory',
    'purchase_orders','inventory_movements','maintenance_records',
    'quality_inspections','customer_complaints','employee_attendance',
    'shipments','operating_costs','safety_incidents','factory_alerts'
  ] loop
    execute format('alter table if exists %I enable row level security', t);
    execute format('drop policy if exists authenticated_read on %I', t);
    execute format('drop policy if exists authenticated_write on %I', t);
    execute format('create policy authenticated_read on %I for select to authenticated using (true)', t);
    execute format('create policy authenticated_write on %I for all to authenticated using (true) with check (true)', t);
  end loop;
end $$;
