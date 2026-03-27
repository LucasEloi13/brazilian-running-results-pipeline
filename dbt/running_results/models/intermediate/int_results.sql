with stg_results as (

    select * from {{ ref('stg_results') }}

),

parsed_distance as (

    select
        *,
        upper(trim(cast(raw_category_name as varchar))) as raw_category_name_norm,
        upper(trim(cast(modality as varchar))) as modality_norm,
        upper(trim(cast(distance_km as varchar))) as distance_km_norm,
        regexp_extract(upper(trim(cast(raw_category_name as varchar))), '([0-9]+([.,][0-9]+)?)', 1) as distance_value_from_raw,
        regexp_extract(upper(trim(cast(raw_category_name as varchar))), '[0-9]+([.,][0-9]+)? *(KM|K|M)', 2) as distance_unit_from_raw,
        regexp_extract(upper(trim(cast(modality as varchar))), '([0-9]+([.,][0-9]+)?)', 1) as distance_value_from_modality,
        regexp_extract(upper(trim(cast(modality as varchar))), '[0-9]+([.,][0-9]+)? *(KM|K|M)', 2) as distance_unit_from_modality,
        regexp_extract(upper(trim(cast(distance_km as varchar))), '([0-9]+([.,][0-9]+)?)', 1) as distance_value_from_distance_col,
        regexp_extract(upper(trim(cast(distance_km as varchar))), '[0-9]+([.,][0-9]+)? *(KM|K|M)', 2) as distance_unit_from_distance_col

    from stg_results

),

resolved_distance as (

    select
        *,
        coalesce(
            try_cast(replace(distance_value_from_raw, ',', '.') as double),
            try_cast(replace(distance_value_from_modality, ',', '.') as double),
            try_cast(replace(distance_value_from_distance_col, ',', '.') as double)
        ) as distance_value_resolved,
        coalesce(
            nullif(distance_unit_from_raw, ''),
            nullif(distance_unit_from_modality, ''),
            nullif(distance_unit_from_distance_col, '')
        ) as distance_unit_resolved

    from parsed_distance

),

normalized as (

    select
        event_id,
        modality_id,
        extraction_job_id,
        extraction_task_id,
        gender,
        is_pcd,
        overall_position,
        category,
        bib,
        athlete_name,
        team,
        pace,
        finish_time,
        gap,
        raw_row_id,
        raw_category_name

    from resolved_distance

)

select * from normalized
