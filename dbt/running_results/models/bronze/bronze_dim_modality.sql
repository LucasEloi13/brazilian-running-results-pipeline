select *
from {{ source('raw', 'dim_modality') }}
