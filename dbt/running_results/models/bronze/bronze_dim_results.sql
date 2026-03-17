select *
from {{ source('raw', 'dim_results') }}
