SELECT
    indicator_name,
    layer_name,
    dataset_name,
    fid,
    timestamp_oqt,
    timestamp_osm,
    result_label,
    result_value,
    result_description,
    result_svg,
    feature
FROM
    results
WHERE
    indicator_name = $1
    AND layer_name = $2
    AND dataset_name = $3
    AND fid = $4
