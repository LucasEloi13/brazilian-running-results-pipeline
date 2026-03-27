{{ config(materialized='view', schema='marts') }}

with int_results as (

    select * from {{ ref('int_results') }}

),

int_events as (

    select * from {{ ref('int_events') }}

),

int_modalities as (

    select * from {{ ref('int_modalities') }}

),

final as (

    select
        r.event_id,
        r.modality_id,
        e.event_slug,
        e.event_name,
        e.event_date,
        e.day,
        e.month,
        e.year,
        e.day_of_week,
        e.is_holiday,
        e.city_id,
        e.city,
        e.state_id,
        e.state,
        e.state_abbreviation,
        m.distance_km,
        m.raw_category_name,
        m.is_pcd as modality_is_pcd,
        r.gender,
        r.is_pcd,
        r.overall_position,
        r.category,
        r.bib,
        r.athlete_name,
        r.team,
        r.pace,
        r.finish_time,
        r.gap,
        r.raw_row_id

    from int_results r
    left join int_events e
        on r.event_id = e.event_id
    left join int_modalities m
        on r.modality_id = m.modality_id

)

select * from final