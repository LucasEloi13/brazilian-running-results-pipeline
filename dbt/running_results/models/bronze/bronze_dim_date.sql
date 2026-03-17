select *
from {{ source('raw', 'dim_date') }}
