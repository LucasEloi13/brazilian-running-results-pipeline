select *
from {{ source('raw', 'dim_event') }}
