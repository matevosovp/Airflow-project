TARGET_TABLE = "public.real_estate_dataset_raw"
STAGING_TABLE = "public.real_estate_dataset_raw_stg"

CREATE_TABLE_SQL = f"""
DROP TABLE IF EXISTS {TARGET_TABLE};
CREATE TABLE {TARGET_TABLE} AS
SELECT
    f.id                AS flat_id,
    f.building_id       AS building_id,
    f.floor             AS floor,
    f.kitchen_area      AS kitchen_area,
    f.living_area       AS living_area,
    f.rooms             AS rooms,
    f.is_apartment      AS is_apartment,
    f.studio            AS studio,
    f.total_area        AS total_area,
    f.price             AS price,
    b.build_year        AS build_year,
    b.building_type_int AS building_type_int,
    b.latitude          AS latitude,
    b.longitude         AS longitude,
    b.ceiling_height    AS ceiling_height,
    b.flats_count       AS flats_count,
    b.floors_total      AS floors_total,
    b.has_elevator      AS has_elevator
FROM public.flats f
JOIN public.buildings b ON b.id = f.building_id
WHERE 1 = 0;
"""

EXTRACT_SQL = f"""
DROP TABLE IF EXISTS {STAGING_TABLE};
CREATE TABLE {STAGING_TABLE} AS
SELECT
    f.id                AS flat_id,
    f.building_id       AS building_id,
    f.floor             AS floor,
    f.kitchen_area      AS kitchen_area,
    f.living_area       AS living_area,
    f.rooms             AS rooms,
    f.is_apartment      AS is_apartment,
    f.studio            AS studio,
    f.total_area        AS total_area,
    f.price             AS price,
    b.build_year        AS build_year,
    b.building_type_int AS building_type_int,
    b.latitude          AS latitude,
    b.longitude         AS longitude,
    b.ceiling_height    AS ceiling_height,
    b.flats_count       AS flats_count,
    b.floors_total      AS floors_total,
    b.has_elevator      AS has_elevator
FROM public.flats f
JOIN public.buildings b ON b.id = f.building_id;
"""

TRANSFORM_SQL = f"""
UPDATE {STAGING_TABLE}
SET
  is_apartment = COALESCE(is_apartment, FALSE),
  studio       = COALESCE(studio, FALSE),
  has_elevator = COALESCE(has_elevator, FALSE);
"""

LOAD_SQL = f"""
INSERT INTO {TARGET_TABLE}
SELECT * FROM {STAGING_TABLE};
"""

CLEANUP_SQL = f"""
DROP TABLE IF EXISTS {STAGING_TABLE};
"""
