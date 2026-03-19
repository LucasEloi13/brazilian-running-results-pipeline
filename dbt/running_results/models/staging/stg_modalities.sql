with source as (
    
    select * from {{ source('raw', 'dim_modality') }}

),

renamed as (

    select
        id as modality_id,
        event_id as event_id,
        distance_km,
        is_pcd, 
        raw_category_name
    
    from source

)

select * from renamed