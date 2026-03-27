with stg_cities as (

    select * from {{ ref('stg_cities') }}

),

int_states as (

    select * from {{ ref('int_states') }}

),

normalized as (

    select
        c.city_id,
        c.city,
        c.state_id,
        s.state,
        s.state_abbreviation

    from stg_cities c
    left join int_states s
        on c.state_id = s.state_id

)

select * from normalized