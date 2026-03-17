select *
from {{ source('raw', 'dim_extraction_task') }}
