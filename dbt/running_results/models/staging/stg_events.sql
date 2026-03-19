with source as (
    
    select *from {{ source('raw', 'dim_event') }}

),

renamed as (

    select
        id      AS event_id,
        slug    AS event_slug,
        name    AS event_name,
        city_id,
        date_id,
        created_at
    
    from source

)

select * from renamed