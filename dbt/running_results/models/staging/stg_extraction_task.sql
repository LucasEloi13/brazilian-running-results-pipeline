with source as (
    
    select * from {{ source('raw', 'dim_extraction_task') }}

),

renamed as (

    select 
        id as extraction_task_id,
        job_id as extraction_job_id,
        modality_id,
        gender,
        source_url,
        status AS extraction_task_status,
        s3_path,
        redshift_loaded,
        row_count as extraction_task_row_count,
        attempts as extraction_task_attempts,
        last_attempt_at as extraction_task_last_attempt_at,
        created_at AS extraction_task_created_at,
        error_msg

    from source

)

select * from renamed