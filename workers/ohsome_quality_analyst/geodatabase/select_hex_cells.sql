WITH bpoly AS (
    SELECT
        ST_Setsrid (public.ST_GeomFromGeoJSON ($1), 4326) AS geom
)
SELECT
    row_to_json(feature_collection)
FROM (
    SELECT
        'FeatureCollection' AS "type",
        array_to_json(array_agg(feature)) AS "features"
    FROM (
        SELECT
            'Feature' AS "type",
            /* Make sure to conform with RFC7946 by using WGS84 lon, lat*/
            ST_AsGeoJSON (ST_Transform (hexcells.wkb_geometry, 4326), 6)::json AS "geometry",
            (
                SELECT
                    json_strip_nulls (row_to_json(t))
                FROM (
                    SELECT
                        tile_id,
                        id
                        ) AS t) AS "properties"
            FROM
                hexcells,
                bpoly
            WHERE
                ST_Intersects (hexcells.wkb_geometry, bpoly.geom)
        ) AS feature
    ) AS feature_collection;
