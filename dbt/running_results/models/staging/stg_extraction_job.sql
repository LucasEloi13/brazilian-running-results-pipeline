with source as (
    
    select * from {{ source('raw', 'dim_extraction_job') }}

), 

renamed as (

    select 
        id as extraction_job_id,
        event_id,
        status AS extraction_job_status,
        created_at AS extraction_job_created_at,
        updated_at AS extraction_job_updated_at

    from source

)

select * from renamed