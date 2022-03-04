import logging
import math
import os
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from io import BytesIO, StringIO
from itertools import product
from statistics import mean
from typing import Dict, List, Literal, NamedTuple, Optional, Tuple

import jinja2
import requests
from dacite import from_dict
from geojson import Feature
from matplotlib import pyplot as plt
from PIL import Image

from ohsome_quality_analyst.base.indicator import BaseIndicator
from ohsome_quality_analyst.utils.definitions import get_metadata
from ohsome_quality_analyst.utils.helper import flatten_dict


@dataclass
class Metadata:
    """Metadata of a report as defined in the metadata.yaml file"""

    name: str
    description: str
    label_description: Dict


@dataclass
class Result:
    """The result of the Report."""

    label: Literal["green", "yellow", "red", "undefined"]
    value: float
    description: str
    html: str


class IndicatorLayer(NamedTuple):
    indicator_name: str
    layer_name: str


class BaseReport(metaclass=ABCMeta):
    """Subclass has to create and append indicator objects to indicators list."""

    def __init__(
        self,
        feature: Feature = None,
        dataset: Optional[str] = None,
        feature_id: Optional[int] = None,
        fid_field: Optional[str] = None,
    ):
        self.dataset = dataset
        self.feature_id = feature_id
        self.fid_field = fid_field
        self.feature = feature

        # Defines indicator+layer combinations
        self.indicator_layer: Tuple[IndicatorLayer] = []
        self.indicators: List[BaseIndicator] = []

        metadata = get_metadata("reports", type(self).__name__)
        self.metadata: Metadata = from_dict(data_class=Metadata, data=metadata)
        # Results will be written during the lifecycle of the report object (combine())
        self.result = Result(None, None, None, None)

    def as_feature(self) -> Feature:
        """Returns a GeoJSON Feature object.

        The properties of the Feature contains the attributes of all indicators.
        The geometry (and properties) of the input GeoJSON object is preserved.
        """
        report_properties = {
            "metadata": vars(self.metadata).copy(),
            "result": vars(self.result).copy(),
        }
        report_properties["metadata"].pop("label_description", None)
        properties = flatten_dict(report_properties, prefix="report")
        for i, indicator in enumerate(self.indicators):
            p = indicator.as_feature()["properties"]
            properties.update(
                {"indicators." + str(i) + "." + str(key): val for key, val in p.items()}
            )
        if "id" in self.feature.keys():
            return Feature(
                id=self.feature.id,
                geometry=self.feature.geometry,
                properties=properties,
            )
        else:
            return Feature(geometry=self.feature.geometry, properties=properties)

    @abstractmethod
    def set_indicator_layer(self) -> None:
        """Set the attribute indicator_layer."""
        pass

    @abstractmethod
    def combine_indicators(self) -> None:
        """Combine indicators results and create the report result object."""
        logging.info(f"Combine indicators for report: {self.metadata.name}")

        values = []
        html = ""
        for indicator in self.indicators:
            if indicator.result.label != "undefined":
                values.append(indicator.result.value)
            if indicator.result.html is not None:
                html += indicator.result.html
                del indicator.result.html
        if not values:
            self.result.value = None
            self.result.label = "undefined"
            self.result.description = "Could not derive quality level"
            return None
        else:
            self.result.value = mean(values)

        if self.result.value < 0.5:
            self.result.label = "red"
            self.result.description = self.metadata.label_description["red"]
        elif self.result.value < 1:
            self.result.label = "yellow"
            self.result.description = self.metadata.label_description["yellow"]
        elif self.result.value >= 1:
            self.result.label = "green"
            self.result.description = self.metadata.label_description["green"]

        dot_css = (
            "style='height: 25px; width: 25px; background-color: {0};"
            "border-radius: 50%; display: inline-block;'"
        )
        traffic_light = (
            "<span {0} class='dot'></span>\n<span {1} class='dot'>"
            "</span>\n<span {2} class='dot'></span>\n Undefined Quality".format(
                dot_css.format("#bbb"),
                dot_css.format("#bbb"),
                dot_css.format("#bbb"),
            )
        )
        color = "grey"
        if self.result.label == "red":
            traffic_light = (
                "<span {0} class='dot'></span>\n<span {1} class='dot'>"
                "</span>\n<span {2} class='dot-red'></span>\n Bad Quality".format(
                    dot_css.format("#FF0000"),
                    dot_css.format("#bbb"),
                    dot_css.format("#bbb"),
                )
            )
            color = "red"
        elif self.result.label == "yellow":
            traffic_light = (
                "<span {0} class='dot'></span>\n<span {1} class='dot-yellow'>"
                "</span>\n<span {2} class='dot'></span>\n Medium Quality".format(
                    dot_css.format("#bbb"),
                    dot_css.format("#FFFF00"),
                    dot_css.format("#bbb"),
                )
            )
            color = "yellow"
        elif self.result.label == "green":
            traffic_light = (
                "<span {0} class='dot-green'></span>\n<span {1} class='dot'>"
                "</span>\n<span {2} class='dot'></span>\n Good Quality".format(
                    dot_css.format("#008000"),
                    dot_css.format("#bbb"),
                    dot_css.format("#bbb"),
                )
            )
            color = "green"

        template_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "templates",
        )
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
        )

        URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png".format

        TILE_SIZE = 256
        x_list = []
        y_list = []
        for coord in self.feature["geometry"]["coordinates"][0][0]:
            x_list.append(coord[0])
            y_list.append(coord[1])
        x_min = min(x_list)
        x_max = max(x_list)
        y_min = min(y_list)
        y_max = max(y_list)

        def point_to_pixels(lon, lat, zoom):
            """convert gps coordinates to web mercator"""
            r = math.pow(2, zoom) * TILE_SIZE
            lat = math.radians(lat)

            x = math.floor((lon + 180.0) / 360.0 * r)
            y = math.ceil(
                (1.0 - math.log(math.tan(lat) + (1.0 / math.cos(lat))) / math.pi)
                / 2.0
                * r
            )

            return x, y

        zoom = 15

        x_outer_0, y_outer_0 = point_to_pixels(x_min, y_min, zoom)
        x_outer_1, y_outer_1 = point_to_pixels(x_max, y_max, zoom)

        x0_tile, y0_tile = int(x_outer_0 / TILE_SIZE), int(y_outer_0 / TILE_SIZE)
        x1_tile, y1_tile = math.ceil(x_outer_1 / TILE_SIZE), math.ceil(
            y_outer_1 / TILE_SIZE
        )

        xmax_tile = max(x0_tile, x1_tile) + 1
        xmin_tile = min(x0_tile, x1_tile) - 1
        ymax_tile = max(y0_tile, y1_tile) + 1
        ymin_tile = min(y0_tile, y1_tile) - 1

        full_x = (xmax_tile - xmin_tile) * TILE_SIZE
        full_y = (ymax_tile - ymin_tile) * TILE_SIZE
        # full size image we'll add tiles to
        img = Image.new("RGB", (full_x, full_y))

        # loop through every tile inside our bounded box
        for x_tile, y_tile in product(
            range(xmin_tile, xmax_tile), range(ymin_tile, ymax_tile)
        ):
            with requests.get(URL(x=x_tile, y=y_tile, z=zoom)) as resp:
                tile_img = Image.open(BytesIO(resp.content))

            # add each tile to the full size image
            img.paste(
                im=tile_img,
                box=(
                    (x_tile - xmin_tile) * TILE_SIZE,
                    (y_tile - ymin_tile) * TILE_SIZE,
                ),
            )

        x, y = xmin_tile * TILE_SIZE, ymin_tile * TILE_SIZE
        left = int(x_outer_0 - x)
        top = int(y_outer_1 - y)
        right = int(x_outer_1 - x)
        bot = int(y_outer_0 - y)

        img = img.crop((left, top, right, bot))

        fig, ax = plt.subplots()
        ax.imshow(img, extent=(x_min, x_max, y_min, y_max))
        ax.add_patch(
            plt.Polygon(
                self.feature["geometry"]["coordinates"][0][0], alpha=0.4, color=color
            )
        )
        svg_string = StringIO()
        plt.savefig(svg_string, format="svg")
        map = svg_string.getvalue()

        template = env.get_template("report_template.html")
        self.result.html = template.render(
            indicators=html,
            result_description=self.result.description,
            metadata=self.metadata.description,
            traffic_light=traffic_light,
            map=map,
        )
