"""Data models of the API request body.

This module uses the library `pydantic` for data validation and
settings management using Python type hinting.

Besides data validation through `pydantic`, `FastAPI` will display additional
information derived from `pydantic` models in the automatic generated API documentation.
"""

from enum import Enum
from typing import Optional, Union

import pydantic
from geojson import Feature, FeatureCollection
from pydantic import BaseModel

from ohsome_quality_analyst.base.layer import LayerData
from ohsome_quality_analyst.utils.definitions import (
    INDICATOR_LAYER,
    get_dataset_names_api,
    get_fid_fields_api,
    get_indicator_names,
    get_layer_names,
    get_report_names,
)
from ohsome_quality_analyst.utils.helper import loads_geojson, snake_to_lower_camel

IndicatorEnum = Enum("IndicatorEnum", {name: name for name in get_indicator_names()})
ReportEnum = Enum("ReportEnum", {name: name for name in get_report_names()})
LayerEnum = Enum("LayerNames", {name: name for name in get_layer_names()})
DatasetEnum = Enum("DatasetNames", {name: name for name in get_dataset_names_api()})
FidFieldEnum = Enum("FidFieldEnum", {name: name for name in get_fid_fields_api()})


class BaseIndicator(BaseModel):
    name: IndicatorEnum = pydantic.Field(
        ..., title="Indicator Name", example="GhsPopComparisonBuildings"
    )
    include_svg: bool = False

    class Config:
        """Pydantic config class."""

        alias_generator = snake_to_lower_camel
        allow_mutation = False
        extra = "forbid"


class BaseReport(BaseModel):
    name: ReportEnum = pydantic.Field(..., title="Report Name", example="SimpleReport")
    include_svg: bool = False

    class Config:
        """Pydantic config class."""

        alias_generator = snake_to_lower_camel
        allow_mutation = False
        extra = "forbid"


class BaseLayerName(BaseModel):
    """Model for the `layer_name` parameter."""

    layer_name: LayerEnum = pydantic.Field(
        ..., title="Layer Name", example="building_count"
    )


class BaseLayerData(BaseModel):
    """Model for the parameter `layer`.

    The Layer consists of name, description and data.
    """

    layer: LayerData


class BaseBpolys(BaseModel):
    """Model for the `bpolys` parameter."""

    bpolys: Union[Feature, FeatureCollection] = pydantic.Field(
        ...,
        title="bpolys",
        example={
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [8.674092292785645, 49.40427147224242],
                        [8.695850372314453, 49.40427147224242],
                        [8.695850372314453, 49.415552187316095],
                        [8.674092292785645, 49.415552187316095],
                        [8.674092292785645, 49.40427147224242],
                    ]
                ],
            },
        },
    )

    @pydantic.validator("bpolys")
    @classmethod
    def validate_bpolys(cls, value) -> dict:
        """Validate GeoJSON."""
        # Load and validate GeoJSON
        for _ in loads_geojson(value):
            # Check if exceptions are raised by `loads_geojson`
            pass
        return value


class BaseDatabase(BaseModel):
    """Model for the combination of parameters: `dataset`, `feature_id`, `fid_field`."""

    dataset: DatasetEnum = pydantic.Field(..., title="Dataset Name", example="regions")
    feature_id: str = pydantic.Field(..., title="Feature Id", example="3")
    fid_field: Optional[FidFieldEnum] = None


class IndicatorBpolys(BaseIndicator, BaseLayerName, BaseBpolys):
    @pydantic.root_validator
    @classmethod
    def validate_indicator_layer(cls, values):
        try:
            indicator_layer = (values["name"].value, values["layer_name"].value)
        except KeyError:
            raise ValueError("An issue with the layer or indicator name occurred.")
        if indicator_layer not in INDICATOR_LAYER:
            raise ValueError(
                "Indicator layer combination is invalid: " + str(indicator_layer)
            )
        else:
            return values


class IndicatorDatabase(BaseIndicator, BaseLayerName, BaseDatabase):
    @pydantic.root_validator
    @classmethod
    def validate_indicator_layer(cls, values):
        try:
            indicator_layer = (values["name"].value, values["layer_name"].value)
        except KeyError:
            raise ValueError("An issue with the layer or indicator name occurred.")
        if indicator_layer not in INDICATOR_LAYER:
            raise ValueError(
                "Indicator layer combination is invalid: " + str(indicator_layer)
            )
        else:
            return values


class IndicatorData(BaseIndicator, BaseLayerData, BaseBpolys):
    @pydantic.validator("name")
    def validate_name(cls, name):  # noqa N805
        if name.value != "MappingSaturation":
            raise ValueError(
                "Computing an Indicator for a Layer with data attached is only "
                + "supported for the Mapping Saturation Indicator."
            )
        else:
            return name


class ReportBpolys(BaseReport, BaseBpolys):
    pass


class ReportDatabase(BaseReport, BaseDatabase):
    pass


INDICATOR_EXAMPLES = {
    "Custom AOI": {
        "summary": "Request an Indicator for a custom AOI (`bpolys`).",
        "description": (
            "The parameter `bpolys` has to be a valid GeoJSON Feature or "
            "FeatureCollection object. The Geometry of those objects has to be Polygon "
            "or MultiPolygon. "
        ),
        "value": {
            "name": "GhsPopComparisonBuildings",
            "layerName": "building_count",
            "bpolys": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [8.674092292785645, 49.40427147224242],
                            [8.695850372314453, 49.40427147224242],
                            [8.695850372314453, 49.415552187316095],
                            [8.674092292785645, 49.415552187316095],
                            [8.674092292785645, 49.40427147224242],
                        ]
                    ],
                },
            },
        },
    },
    "OQT AOI": {
        "summary": (
            "Request an Indicator for an AOI defined by OQT (`dataset` and "
            "`featureId`)."
        ),
        "description": (
            "Specify `dataset` and `featureId` to request an already calculated "
            "Indicator for an AOI defined by OQT."
        ),
        "value": {
            "name": "GhsPopComparisonBuildings",
            "layerName": "building_count",
            "dataset": "regions",
            "featureId": 3,
        },
    },
    "Custom AOI and custom Layer": {
        "summary": (
            "Request an Indicator for a custom AOI (`bpolys`) and a custom Layer "
            "(`layer`)."
        ),
        "description": (
            "The Layer must have a name and description. The data associated with this "
            "Layer must be provided as well. "
        ),
        "value": {
            "name": "MappingSaturation",
            "bpolys": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [8.674092292785645, 49.40427147224242],
                            [8.695850372314453, 49.40427147224242],
                            [8.695850372314453, 49.415552187316095],
                            [8.674092292785645, 49.415552187316095],
                            [8.674092292785645, 49.40427147224242],
                        ]
                    ],
                },
            },
            "layer": {
                "name": "",
                "description": "",
                "data": {
                    "result": [
                        {"value": v, "timestamp": "2020-03-20T01:30:08.180856"}
                        for v in [
                            1.0,
                            1.0,
                            1.0,
                            1.0,
                            1.0,
                            4.0,
                            44.0,
                            114.0,
                            226.0,
                            241.0,
                            252.0,
                            266.0,
                            272.0,
                            275.0,
                            279.0,
                            298.0,
                            306.0,
                            307.0,
                            426.0,
                            430.0,
                            472.0,
                            482.0,
                            498.0,
                            502.0,
                            543.0,
                            555.0,
                            557.0,
                            607.0,
                            610.0,
                            631.0,
                            637.0,
                            655.0,
                            660.0,
                            695.0,
                            695.0,
                            1011.0,
                            5669.0,
                            7217.0,
                            8579.0,
                            8755.0,
                            8990.0,
                            9043.0,
                            9288.0,
                            9412.0,
                            9670.0,
                            9721.0,
                            9734.0,
                            9773.0,
                            10068.0,
                            10416.0,
                            10521.0,
                            10537.0,
                            10754.0,
                            10840.0,
                            10957.0,
                            11477.0,
                            11530.0,
                            11718.0,
                            11767.0,
                            11981.0,
                            12067.0,
                            12646.0,
                            12925.0,
                            13698.0,
                            14369.0,
                            15360.0,
                            15449.0,
                            15564.0,
                            15743.0,
                            16052.0,
                            16459.0,
                            17613.0,
                            18721.0,
                            19786.0,
                            20600.0,
                            21283.0,
                            21587.0,
                            21712.0,
                            21903.0,
                            22655.0,
                            22860.0,
                            23022.0,
                            23200.0,
                            23253.0,
                            23491.0,
                            23541.0,
                            23608.0,
                            23652.0,
                            23701.0,
                            23721.0,
                            23792.0,
                            23814.0,
                            23955.0,
                            23982.0,
                            24037.0,
                            24124.0,
                            24203.0,
                            24805.0,
                            24809.0,
                            24960.0,
                            25138.0,
                            25650.0,
                            25692.0,
                            25869.0,
                            26255.0,
                            26265.0,
                            26313.0,
                            26330.0,
                            26456.0,
                            26549.0,
                            26553.0,
                            26592.0,
                            26690.0,
                            26760.0,
                            26931.0,
                            26920.0,
                            27074.0,
                            27113.0,
                            27139.0,
                            27369.0,
                            27456.0,
                            28372.0,
                            28837.0,
                            28900.0,
                            28945.0,
                            28948.0,
                            28953.0,
                            28954.0,
                            28954.0,
                            28957.0,
                            29003.0,
                            29047.0,
                            29091.0,
                            29109.0,
                            29137.0,
                            29179.0,
                            29202.0,
                            29271.0,
                            29270.0,
                            29267.0,
                            29287.0,
                            29297.0,
                            29301.0,
                            29321.0,
                            29330.0,
                            29334.0,
                            29348.0,
                            29378.0,
                            29406.0,
                            29501.0,
                            29523.0,
                            29548.0,
                            29551.0,
                            29606.0,
                            29624.0,
                            29634.0,
                            29631.0,
                            29642.0,
                            29702.0,
                            29697.0,
                            29696.0,
                            29792.0,
                            29800.0,
                            29806.0,
                        ]
                    ]
                },
            },
        },
    },
}

REPORT_EXAMPLES = {
    "Custom AOI": {
        "summary": "Request a Report for a custom AOI (`bpolys`).",
        "description": (
            "The parameter `bpolys` has to be a valid GeoJSON Feature or "
            "FeatureCollection object. The Geometry of those objects has to be Polygon "
            "or MultiPolygon. "
        ),
        "value": {
            "name": "SimpleReport",
            "bpolys": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [8.674092292785645, 49.40427147224242],
                            [8.695850372314453, 49.40427147224242],
                            [8.695850372314453, 49.415552187316095],
                            [8.674092292785645, 49.415552187316095],
                            [8.674092292785645, 49.40427147224242],
                        ]
                    ],
                },
            },
        },
    },
    "OQT AOI": {
        "summary": (
            "Request a Report for a AOI defined by OQT (`dataset` and `featureId`)."
        ),
        "description": (
            "Specify `dataset` and `featureId` to request an already calculated "
            "Report for an AOI defined by OQT."
        ),
        "value": {
            "name": "SimpleReport",
            "dataset": "regions",
            "featureId": 3,
        },
    },
}
