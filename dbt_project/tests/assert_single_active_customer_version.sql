-- Prevent the SCD join from multiplying fact rows and inflating revenue.
select customer_id, count(*) as active_versions
from {{ ref('stg_customers') }}
where is_active = true
group by customer_id
having count(*) > 1
