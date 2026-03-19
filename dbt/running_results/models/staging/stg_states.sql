with source as (
    
    select * from {{ source('raw', 'dim_state') }}

),

renamed as (

    select
        id as state_id,
        name as state, 
        abbreviation as state_abbreviation
    
    from source

)

select * from renamed
