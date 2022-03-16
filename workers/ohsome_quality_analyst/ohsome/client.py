import datetime
import logging
from typing import Optional, Union

import geojson
import httpx
from geojson import Feature, FeatureCollection, MultiPolygon, Polygon

# `geojson` uses `simplejson` if it is installed
try:
    from simplejson import JSONDecodeError
except ImportError:
    from json import JSONDecodeError

from ohsome_quality_analyst.utils.definitions import OHSOME_API, USER_AGENT
from ohsome_quality_analyst.utils.exceptions import OhsomeApiError


# TODO: Add more tests for ohsome package.
async def query(
    layer,
    bpolys: Feature,
    time: Optional[str] = None,
) -> dict:
    """
    Query ohsome API endpoint with filter.

    Time is one or more ISO-8601 conform timestring(s).
    https://docs.ohsome.org/ohsome-api/v1/time.html
    """
    url = "/".join(
        OHSOME_API.rstrip("/"),
        layer.endpoint.rstrip("/"),
    )
    data = build_data_dict(
        FeatureCollection(bpolys),
        layer,
        time,
    )
    logging.info("Query ohsome API.")
    return await query_ohsome_api(url, data)


# TODO: Multidispatch
async def query(
    layer,
    bpolys: FeatureCollection,
    time: Optional[str] = None,
) -> dict:
    """
    Query ohsome API endpoint with filter.

    Time is one or more ISO-8601 conform timestring(s).
    https://docs.ohsome.org/ohsome-api/v1/time.html
    """
    url = "/".join(
        OHSOME_API.rstrip("/"),
        layer.endpoint.rstrip("/"),
        "groupBy",
        "boundary",
    )
    data = build_data_dict(
        bpolys,
        layer,
        time,
    )
    logging.info("Query ohsome API.")
    return await query_ohsome_api(url, data)


async def query_ohsome_api(url: str, data: dict) -> dict:
    """Query the ohsome API.

    A custom connection timeout is set since the ohsome API can take a long time to
    send an answer (< 10 minutes).

    Raises:
        OhsomeApiError: In case of 4xx and 5xx response status codes or invalid
            response due to timeout during streaming.

    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(300, read=660)) as client:
        resp = await client.post(
            url,
            data=data,
            headers={"user-agent": USER_AGENT},
        )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise OhsomeApiError(
            "Querying the ohsome API failed! " + error.response.json()["message"]
        ) from error
    try:
        return geojson.loads(resp.content)
    except JSONDecodeError as error:
        raise OhsomeApiError(
            "Ohsome API returned invalid GeoJSON after streaming of the response. "
            + "The reason is a timeout of the ohsome API."
        ) from error


async def get_latest_ohsome_timestamp() -> datetime.datetime:
    """Get unix timestamp of ohsome from ohsome api."""
    url = "https://api.ohsome.org/v1/metadata"
    headers = {"user-agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
    timestamp_str = str(resp.json()["extractRegion"]["temporalExtent"]["toTimestamp"])
    timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%MZ")
    return timestamp


def build_data_dict(
    bpolys: FeatureCollection,
    layer: Layer,
    time: Optional[str] = None,
) -> dict:
    """Build data dictionary for ohsome API query."""
    if time:
        return {
            "bpolys": bpolys,
            "filter": layer.filter,
            "time": time,
        }
    else:
        return {
            "bpolys": bpolys,
            "filter": layer.filter,
        }
