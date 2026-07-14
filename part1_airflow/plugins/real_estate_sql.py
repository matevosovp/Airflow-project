from config import (
    BUILDINGS_TABLE,
    FLATS_TABLE,
    RAW_STAGING_TABLE,
    RAW_TABLE,
)

RAW_STAGING_INDEX = "real_estate_dataset_raw_stg_flat_id_uidx"
RAW_INDEX = "real_estate_dataset_raw_flat_id_uidx"


VALIDATE_SOURCE_SQL = f"""
DO $$
DECLARE
    orphan_count BIGINT;
BEGIN
    IF to_regclass('{FLATS_TABLE}') IS NULL THEN
        RAISE EXCEPTION 'Source table {FLATS_TABLE} does not exist';
    END IF;

    IF to_regclass('{BUILDINGS_TABLE}') IS NULL THEN
        RAISE EXCEPTION 'Source table {BUILDINGS_TABLE} does not exist';
    END IF;

    SELECT COUNT(*)
    INTO orphan_count
    FROM {FLATS_TABLE} AS f
    LEFT JOIN {BUILDINGS_TABLE} AS b ON b.id = f.building_id
    WHERE b.id IS NULL;

    IF orphan_count > 0 THEN
        RAISE EXCEPTION
            'Found % flats without a matching building; refusing a lossy join',
            orphan_count;
    END IF;
END $$;
"""


BUILD_RAW_DATASET_SQL = f"""
DROP TABLE IF EXISTS {RAW_STAGING_TABLE};

CREATE TABLE {RAW_STAGING_TABLE} AS
SELECT
    f.id AS flat_id,
    f.building_id AS building_id,
    f.floor AS floor,
    f.kitchen_area AS kitchen_area,
    f.living_area AS living_area,
    f.rooms AS rooms,
    COALESCE(f.is_apartment, FALSE) AS is_apartment,
    COALESCE(f.studio, FALSE) AS studio,
    f.total_area AS total_area,
    f.price AS price,
    b.build_year AS build_year,
    b.building_type_int AS building_type_int,
    b.latitude AS latitude,
    b.longitude AS longitude,
    b.ceiling_height AS ceiling_height,
    b.flats_count AS flats_count,
    b.floors_total AS floors_total,
    COALESCE(b.has_elevator, FALSE) AS has_elevator
FROM {FLATS_TABLE} AS f
INNER JOIN {BUILDINGS_TABLE} AS b ON b.id = f.building_id;

DO $$
DECLARE
    row_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO row_count
    FROM {RAW_STAGING_TABLE};

    IF row_count = 0 THEN
        RAISE EXCEPTION 'Raw dataset build produced zero rows';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM {RAW_STAGING_TABLE}
        WHERE flat_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Raw dataset contains NULL flat_id values';
    END IF;

    IF EXISTS (
        SELECT flat_id
        FROM {RAW_STAGING_TABLE}
        GROUP BY flat_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Raw dataset contains duplicate flat_id values';
    END IF;
END $$;

CREATE UNIQUE INDEX {RAW_STAGING_INDEX}
    ON {RAW_STAGING_TABLE} (flat_id);

ANALYZE {RAW_STAGING_TABLE};

DROP TABLE IF EXISTS {RAW_TABLE};
ALTER TABLE {RAW_STAGING_TABLE}
    RENAME TO real_estate_dataset_raw;
ALTER INDEX public.{RAW_STAGING_INDEX}
    RENAME TO {RAW_INDEX};
"""
