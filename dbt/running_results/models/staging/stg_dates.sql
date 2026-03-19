with source as (
    
    select * from {{ source('raw', 'dim_date') }}

),

renamed as (

    select
        id as date_id,
        date as event_date,
        day,
        month,
        year,
        day_of_week,
        is_holiday
    
    from source

)

select * from renamed