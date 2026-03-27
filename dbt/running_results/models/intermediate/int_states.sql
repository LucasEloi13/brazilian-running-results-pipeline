with stg_states as (

    select * from {{ ref('stg_states') }}

),

normalized as (

    select
        state_id,
        state,
        upper(trim(state_abbreviation)) as state_abbreviation

    from stg_states

)

select * from normalized