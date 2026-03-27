with stg_dates as (

    select * from {{ ref('stg_dates') }}

),

normalized as (

    select
        date_id,
        event_date,
        day,
        month,
        year,
        day_of_week,
        is_holiday

    from stg_dates

)

select * from normalized