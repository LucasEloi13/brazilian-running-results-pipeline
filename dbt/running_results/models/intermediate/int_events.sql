with stg_events as (

    select * from {{ ref('stg_events') }}

),

int_cities as (

    select * from {{ ref('int_cities') }}

),

int_dates as (

    select * from {{ ref('int_dates') }}

),

normalized as (

    select
        e.event_id,
        e.event_slug,
        e.event_name,
        e.city_id,
        c.city,
        c.state_id,
        c.state,
        c.state_abbreviation,
        e.date_id,
        d.event_date,
        d.day,
        d.month,
        d.year,
        d.day_of_week,
        d.is_holiday,
        e.created_at as event_created_at

    from stg_events e
    left join int_cities c
        on e.city_id = c.city_id
    left join int_dates d
        on e.date_id = d.date_id

)

select * from normalized