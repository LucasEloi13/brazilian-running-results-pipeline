with source as (
    
    select * from {{ source('raw', 'dim_results') }}

),


-- state
-- city
-- modality
-- pcd
-- gender_partition
-- event
-- geral
-- cat
-- numero
-- nome
-- equipe
-- pace
-- tempo
-- gap
-- raw_row_id
-- overall
-- category
-- bib
-- athlete_name
-- team
-- finish_time
-- job_id
-- task_id
-- event_id
-- modality_id
-- gender
-- distance_km
-- is_pcd
-- raw_category_name





renamed as (

    select
        --ids
        job_id,
        task_id,
        event_id,
        modality_id,

        --dimensions
        modality,
        gender_partition as gender,


    
    from source

)

