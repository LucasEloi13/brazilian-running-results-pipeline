with source as (

    select * from {{ source('raw', 'dim_city') }}    

), 

renamed as (

    select 
        id as city_id,
        name as city,
        state_id
    
    from source

)

select * from renamed
