import os
from dataclasses import dataclass
from string import Template

import dateutil.parser
import pandas as pd
from dacite import from_dict

# import matplotlib.pyplot as plt
from geojson import Feature

import ohsome_quality_analyst.geodatabase.client as db_client
from ohsome_quality_analyst.base.indicator import BaseIndicator
from ohsome_quality_analyst.ohsome import client as ohsome_client
from ohsome_quality_analyst.raster import client as raster_client
from ohsome_quality_analyst.utils.definitions import get_raster_dataset
from ohsome_quality_analyst.utils.helper import load_sklearn_model


@dataclass
class Covariates:
    ghs_pop: float  # Pop density in sqkm
    shdi: float  # Mean
    vnl: float  # Sum
    # GHSL SMOD L2 nomenclature
    urban_centre: float = 0.0
    dense_urban_cluster: float = 0.0
    semi_dense_urban_cluster: float = 0.0
    suburban_or_peri_urban: float = 0.0
    rural_cluster: float = 0.0
    low_density_rural: float = 0.0
    very_low_density_rural: float = 0.0
    water: float = 0.0


class BuildingArea(BaseIndicator):
    """Building Area Indicator

    Predict the expected building area covering the feature based on population,
    nighttime light, subnational HDI value, and GHS Settlement Model grid using a
    trained random forest regressor. The expected building area is compared to the
    building area mapped in OSM.

    The result depends on the percentage the OSM mapping reaches compared of the
    expected area.

    Args:
        layer_name (str): Layer name has to reference a building area Layer.
            Unit is in meter.
        feature (Feature): GeoJSON Feature object

    """

    def __init__(
        self,
        layer_name: str,
        feature: Feature,
    ) -> None:
        super().__init__(
            layer_name=layer_name,
            feature=feature,
        )
        self.model_name = "Random Forest Regressor"
        self.covariates: Covariates = None
        self.building_area_osm = None
        self.building_area_prediction = None
        self.percentage_mapped = None
        self.attrdict = None

    async def preprocess(self) -> None:
        query_results = await ohsome_client.query(
            layer=self.layer,
            bpolys=self.feature.geometry,
        )
        self.building_area = query_results["results"][0]["value"]
        self.result.timestamp_osm = dateutil.parser.isoparse(
            query_results["result"][0]["timestamp"]
        )

        self.covariates = from_dict(
            data_class=Covariates,
            data={
                **get_smod_class_share(self.feature),
                "ghs_pop": get_ghs_pop_density(self.feature),
                "vnl": raster_client.get_zonal_stats(
                    self.feature,
                    get_raster_dataset("VNL"),
                    stats="sum",
                )[0].get("sum"),
                # TODO: Waiting for PR 266
                # "shdi": db_client.get_shdi(self.feature.geometry)
                "shdi": 0.5,
            },
        )

    def calculate(self) -> None:
        directory = os.path.dirname(os.path.abspath(__file__))
        scaler = load_sklearn_model(os.path.join(directory, "scaler.joblib"))
        model = load_sklearn_model(os.path.join(directory, "model.joblib"))

        # create a DataFrame from dict, as the regressor was trained with one
        x = pd.DataFrame.from_dict([self.attrdict])

        # define which values in the df must be normalised
        columns_to_normalize = [
            "ghspop",
            "ghspop_density_per_sqkm",
            "vnl_sum",
        ]

        # get the values to be normalized
        values_unnormalized = x[columns_to_normalize].values  # returns a numpy array
        # get normalized values
        values_scaled = scaler.transform(values_unnormalized)
        # insert normalized values in original df
        x[columns_to_normalize] = values_scaled

        # use model to predict building area
        y = model.predict(x)
        self.building_area_prediction = y[0]

        # calculate percentage OSM reached compared to expected value
        self.percentage_mapped = (
            self.building_area_osm / self.building_area_prediction
        ) * 100

        description = Template(self.metadata.result_description).substitute(
            building_area=self.building_area,
            predicted_building_area=self.predicted_building_area,
            percentage_mapped=self.percentage_mapped,
        )
        # TODO: adjust percentage boundaries for green/yellow/red. Adjust in medata.yaml
        #       as well
        if self.percentage_mapped >= 95.0:
            self.result.label = "green"
            self.result.value = 1.0
            self.result.description = (
                description + self.metadata.label_description["green"]
            )
        # growth is larger than 3% within last 3 years
        elif 95.0 > self.percentage_mapped >= 75.0:
            self.result.label = "yellow"
            self.result.value = 0.5
            self.result.description = (
                description + self.metadata.label_description["yellow"]
            )
        # growth level is better than the red threshold
        else:
            self.result.label = "red"
            self.result.value = 0.0
            self.result.description = (
                description + self.metadata.label_description["red"]
            )

    def create_figure(self) -> None:
        raise NotImplementedError


def get_smod_class_share(feature) -> dict:
    """Get the share of each GHSL SMOD L2 class for the AOI.

    Returns:
        dict: Keys are the category names. Values are the share of the class (0, 1)
    """
    category_map = {
        30: "urban_centre",
        23: "dense_urban_cluster",
        22: "semi_dense_urban_cluster",
        21: "suburban_or_peri_urban",
        13: "rural_cluster",
        12: "low_density_rural",
        11: "very_low_density_rural",
        10: "water",
    }
    # Get a dict containing unique raster values as keys and pixel counts as values
    class_count: dict = raster_client.get_zonal_stats(
        feature,
        get_raster_dataset("GHS_SMOD_R2019A"),
        categorical=True,
        category_map=category_map,
    )[0]
    pixel_count = raster_client.get_zonal_stats(
        feature,
        get_raster_dataset("GHS_SMOD_R2019A"),
        stats="count",
    )[0].get("count")
    return {k: v / pixel_count for k, v in class_count.items()}


async def get_ghs_pop_density(feature) -> float:
    """Get population density using GHSL GHS-POP."""
    ghs_pop_sum = raster_client.get_zonal_stats(
        feature,
        get_raster_dataset("GHS_POP_R2019A"),
        stats="sum",
    )[0]["sum"]
    area = await db_client.get_area_of_bpolys(feature.geometry)
    return ghs_pop_sum / area


# TOOO: define self.model_name (see TODO above)
# TODO: check, whether raster containing no value and therefore indicator should be
#           undefined
# TODO: implement shdi mean querry (see TODO above)
# TODO: discuss & adjust percentage boundaries for green/yellow/red. Adjust values in
#           metadata.yaml as well(see TODO above)
# TODO: discuss: as the regressor is only trained with samples from africa, make it
#           usable for features in africa only?
