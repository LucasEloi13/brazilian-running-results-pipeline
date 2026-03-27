with source as (
    
    select * from {{ source('raw', 'dim_results') }}

),

renamed as (

    select
        state,
        city,
        modality,
        pcd as pcd_partition,
        gender_partition,
        event,
        geral as overall_position_raw,
        cat as category_raw,
        numero as bib_raw,
        nome as athlete_name_raw,
        equipe as team_raw,
        pace,
        tempo as finish_time_raw,
        gap,
        raw_row_id,
        overall as overall_position,
        category,
        bib,
        athlete_name,
        team,
        finish_time,
        job_id as extraction_job_id,
        task_id as extraction_task_id,
        event_id,
        modality_id,
        gender,
        distance_km,
        is_pcd,
        raw_category_name

    from source

)

select * from renamed
