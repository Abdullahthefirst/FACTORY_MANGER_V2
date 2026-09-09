-- Reporting views used by the manager dashboard.
create or replace view manager_inventory_status as
select i.id, i.material_id, m.material_code, m.name as material_name,
       i.quantity, m.unit, m.reorder_level,
       greatest(m.reorder_level - i.quantity, 0) as reorder_gap,
       case when i.quantity <= 0 then 'Critical'
            when i.quantity <= m.reorder_level then 'Low Stock'
            else 'Healthy' end as stock_status,
       i.warehouse_location, i.last_updated
from inventory i join materials m on m.id = i.material_id;

create or replace view manager_production_daily as
select production_date, sum(planned_quantity) as planned_quantity,
       sum(actual_quantity) as actual_quantity, sum(rejected_quantity) as rejected_quantity,
       sum(downtime_minutes) as downtime_minutes,
       case when sum(planned_quantity) > 0
            then round(sum(actual_quantity) / sum(planned_quantity) * 100, 2)
            else 0 end as efficiency_percent
from production_records group by production_date;
