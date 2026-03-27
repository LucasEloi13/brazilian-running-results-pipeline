with stg_modalities as (

    select * from {{ ref('stg_modalities') }}

),

parsed_distance as (

    select
        *,
        regexp_extract(upper(trim(cast(raw_category_name as varchar))), '([0-9]+([.,][0-9]+)?)', 1) as distance_value_text,
        regexp_extract(upper(trim(cast(raw_category_name as varchar))), '[0-9]+([.,][0-9]+)? *(KM|K|M)', 2) as distance_unit

    from stg_modalities

),

normalized as (

    select
        modality_id,
        event_id,
        is_pcd,
        raw_category_name,
        cast(
            case
                when try_cast(replace(distance_value_text, ',', '.') as double) is null
                    then try_cast(distance_km as double)
                when distance_unit in ('KM', 'K')
                    then try_cast(replace(distance_value_text, ',', '.') as double)
                when distance_unit = 'M'
                    then try_cast(replace(distance_value_text, ',', '.') as double) / 1000.0
                when distance_unit is null
                     and try_cast(replace(distance_value_text, ',', '.') as double) >= 100
                    then try_cast(replace(distance_value_text, ',', '.') as double) / 1000.0
                else try_cast(replace(distance_value_text, ',', '.') as double)
            end as double
        ) as distance_km

    from parsed_distance

)

select * from normalized