from config import (
    CLEAN_STAGING_TABLE,
    CLEAN_TABLE,
    DB_SCHEMA,
    RAW_TABLE,
)

CLEAN_TABLE_NAME = CLEAN_TABLE.rsplit(".", maxsplit=1)[-1]
CLEAN_STAGING_INDEX = "real_estate_dataset_clean_stg_flat_id_uidx"
CLEAN_INDEX = "real_estate_dataset_clean_flat_id_uidx"


VALIDATE_RAW_DATASET_SQL = f"""
DO $$
BEGIN
    IF to_regclass('{RAW_TABLE}') IS NULL THEN
        RAISE EXCEPTION
            'Source table {RAW_TABLE} does not exist; run real_estate_dataset_etl first';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM {RAW_TABLE}) THEN
        RAISE EXCEPTION 'Source table {RAW_TABLE} is empty';
    END IF;
END $$;
"""


BUILD_CLEAN_DATASET_SQL = f"""
DROP TABLE IF EXISTS {CLEAN_STAGING_TABLE};

CREATE TABLE {CLEAN_STAGING_TABLE} AS
WITH base AS (
    SELECT
        flat_id,
        building_id,
        floor,
        kitchen_area,
        living_area,
        rooms,
        is_apartment,
        studio,
        total_area,
        price,
        build_year,
        building_type_int,
        latitude,
        longitude,
        ceiling_height,
        flats_count,
        floors_total,
        has_elevator
    FROM {RAW_TABLE}
    WHERE flat_id IS NOT NULL
      AND building_id IS NOT NULL
      AND price IS NOT NULL
      AND price > 0
      AND rooms IS NOT NULL
      AND rooms > 0
),
feature_statistics AS (
    SELECT
        percentile_cont(0.5) WITHIN GROUP (ORDER BY floor)
            FILTER (WHERE floor IS NOT NULL) AS floor_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY kitchen_area)
            FILTER (WHERE kitchen_area IS NOT NULL) AS kitchen_area_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY living_area)
            FILTER (WHERE living_area IS NOT NULL) AS living_area_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY total_area)
            FILTER (WHERE total_area IS NOT NULL) AS total_area_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY build_year)
            FILTER (WHERE build_year IS NOT NULL) AS build_year_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY latitude)
            FILTER (WHERE latitude IS NOT NULL) AS latitude_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY longitude)
            FILTER (WHERE longitude IS NOT NULL) AS longitude_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY ceiling_height)
            FILTER (WHERE ceiling_height IS NOT NULL) AS ceiling_height_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY flats_count)
            FILTER (WHERE flats_count IS NOT NULL) AS flats_count_median,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY floors_total)
            FILTER (WHERE floors_total IS NOT NULL) AS floors_total_median,
        mode() WITHIN GROUP (ORDER BY building_type_int)
            FILTER (WHERE building_type_int IS NOT NULL) AS building_type_mode
    FROM base
),
imputed AS (
    SELECT
        d.flat_id,
        d.building_id,
        COALESCE(d.floor, s.floor_median) AS floor,
        COALESCE(d.kitchen_area, s.kitchen_area_median) AS kitchen_area,
        COALESCE(d.living_area, s.living_area_median) AS living_area,
        d.rooms,
        COALESCE(d.is_apartment, FALSE) AS is_apartment,
        COALESCE(d.studio, FALSE) AS studio,
        COALESCE(d.total_area, s.total_area_median) AS total_area,
        d.price,
        COALESCE(d.build_year, s.build_year_median) AS build_year,
        COALESCE(d.building_type_int, s.building_type_mode) AS building_type_int,
        COALESCE(d.latitude, s.latitude_median) AS latitude,
        COALESCE(d.longitude, s.longitude_median) AS longitude,
        COALESCE(d.ceiling_height, s.ceiling_height_median) AS ceiling_height,
        COALESCE(d.flats_count, s.flats_count_median) AS flats_count,
        COALESCE(d.floors_total, s.floors_total_median) AS floors_total,
        COALESCE(d.has_elevator, FALSE) AS has_elevator
    FROM base AS d
    CROSS JOIN feature_statistics AS s
),
consistent AS (
    SELECT
        flat_id,
        building_id,
        floor,
        kitchen_area,
        living_area,
        rooms,
        is_apartment,
        studio,
        total_area,
        price,
        build_year,
        building_type_int,
        latitude,
        longitude,
        ceiling_height,
        flats_count,
        floors_total,
        has_elevator
    FROM imputed
    WHERE total_area > 0
      AND kitchen_area > 0
      AND living_area > 0
      AND kitchen_area <= total_area
      AND living_area <= total_area
      AND (floor IS NULL OR floor >= 0)
      AND (floors_total IS NULL OR floors_total > 0)
      AND (floor IS NULL OR floors_total IS NULL OR floor <= floors_total)
),
iqr_bounds AS (
    SELECT
        percentile_cont(0.25) WITHIN GROUP (ORDER BY price) AS price_q1,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY price) AS price_q3,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY total_area) AS total_area_q1,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY total_area) AS total_area_q3,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY kitchen_area) AS kitchen_area_q1,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY kitchen_area) AS kitchen_area_q3,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY living_area) AS living_area_q1,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY living_area) AS living_area_q3
    FROM consistent
),
capped AS (
    SELECT
        d.flat_id,
        d.building_id,
        d.floor,
        CASE
            WHEN b.kitchen_area_q1 IS NULL OR b.kitchen_area_q3 <= b.kitchen_area_q1
                THEN d.kitchen_area
            ELSE GREATEST(
                b.kitchen_area_q1 - 1.5 * (b.kitchen_area_q3 - b.kitchen_area_q1),
                LEAST(
                    d.kitchen_area,
                    b.kitchen_area_q3 + 1.5 * (b.kitchen_area_q3 - b.kitchen_area_q1)
                )
            )
        END AS kitchen_area,
        CASE
            WHEN b.living_area_q1 IS NULL OR b.living_area_q3 <= b.living_area_q1
                THEN d.living_area
            ELSE GREATEST(
                b.living_area_q1 - 1.5 * (b.living_area_q3 - b.living_area_q1),
                LEAST(
                    d.living_area,
                    b.living_area_q3 + 1.5 * (b.living_area_q3 - b.living_area_q1)
                )
            )
        END AS living_area,
        d.rooms,
        d.is_apartment,
        d.studio,
        CASE
            WHEN b.total_area_q1 IS NULL OR b.total_area_q3 <= b.total_area_q1
                THEN d.total_area
            ELSE GREATEST(
                b.total_area_q1 - 1.5 * (b.total_area_q3 - b.total_area_q1),
                LEAST(
                    d.total_area,
                    b.total_area_q3 + 1.5 * (b.total_area_q3 - b.total_area_q1)
                )
            )
        END AS total_area,
        CASE
            WHEN b.price_q1 IS NULL OR b.price_q3 <= b.price_q1
                THEN d.price
            ELSE GREATEST(
                b.price_q1 - 1.5 * (b.price_q3 - b.price_q1),
                LEAST(d.price, b.price_q3 + 1.5 * (b.price_q3 - b.price_q1))
            )
        END AS price,
        d.build_year,
        d.building_type_int,
        d.latitude,
        d.longitude,
        d.ceiling_height,
        d.flats_count,
        d.floors_total,
        d.has_elevator
    FROM consistent AS d
    CROSS JOIN iqr_bounds AS b
)
SELECT
    flat_id,
    building_id,
    floor,
    kitchen_area,
    living_area,
    rooms,
    is_apartment,
    studio,
    total_area,
    price,
    build_year,
    building_type_int,
    latitude,
    longitude,
    ceiling_height,
    flats_count,
    floors_total,
    has_elevator
FROM capped
WHERE kitchen_area <= total_area
  AND living_area <= total_area;

DO $$
DECLARE
    row_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO row_count
    FROM {CLEAN_STAGING_TABLE};

    IF row_count = 0 THEN
        RAISE EXCEPTION 'Clean dataset build produced zero rows';
    END IF;

    IF EXISTS (
        SELECT flat_id
        FROM {CLEAN_STAGING_TABLE}
        GROUP BY flat_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Clean dataset contains duplicate flat_id values';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM {CLEAN_STAGING_TABLE}
        WHERE flat_id IS NULL
           OR building_id IS NULL
           OR price IS NULL
           OR price <= 0
           OR rooms IS NULL
           OR rooms <= 0
           OR total_area IS NULL
           OR total_area <= 0
           OR kitchen_area IS NULL
           OR kitchen_area <= 0
           OR living_area IS NULL
           OR living_area <= 0
           OR kitchen_area > total_area
           OR living_area > total_area
    ) THEN
        RAISE EXCEPTION 'Clean dataset failed business-rule validation';
    END IF;
END $$;

CREATE UNIQUE INDEX {CLEAN_STAGING_INDEX}
    ON {CLEAN_STAGING_TABLE} (flat_id);

ANALYZE {CLEAN_STAGING_TABLE};

DROP TABLE IF EXISTS {CLEAN_TABLE};
ALTER TABLE {CLEAN_STAGING_TABLE}
    RENAME TO {CLEAN_TABLE_NAME};
ALTER INDEX {DB_SCHEMA}.{CLEAN_STAGING_INDEX}
    RENAME TO {CLEAN_INDEX};
"""
