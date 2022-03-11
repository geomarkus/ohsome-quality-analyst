import os
from dataclasses import asdict, dataclass
from string import Template

import dateutil.parser
from dacite import from_dict

# import matplotlib.pyplot as plt
from geojson import Feature

import ohsome_quality_analyst.geodatabase.client as db_client
from ohsome_quality_analyst.base.indicator import BaseIndicator
from ohsome_quality_analyst.ohsome import client as ohsome_client
from ohsome_quality_analyst.raster import client as raster_client
from ohsome_quality_analyst.utils.definitions import get_raster_dataset
from ohsome_quality_analyst.utils.helper import load_sklearn_model


@dataclass(frozen=True, order=True)
class Covariates:
    """Covariates/Input Sample for the Random Forest Regressor.

    The order is of the input sample is important.
    """

    # GHSL GHS-POP
    ghs_pop: float
    ghs_pop_density: float  # [sqkm]
    # GHSL SMOD L2 nomenclature
    water: float = 0.0
    very_low_density_rural: float = 0.0
    low_density_rural: float = 0.0
    rural_cluster: float = 0.0
    suburban_or_peri_urban: float = 0.0
    semi_dense_urban_cluster: float = 0.0
    dense_urban_cluster: float = 0.0
    urban_centre: float = 0.0
    # GDL SHDI
    shdi: float = 0.0  # Mean
    # EOG VNL
    vnl: float = 0.0  # Sum


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

    async def preprocess(self) -> None:
        # Get OSM data
        query_results = await ohsome_client.query(
            layer=self.layer,
            bpolys=self.feature.geometry,
        )
        self.building_area_osm = query_results["result"][0]["value"]
        self.result.timestamp_osm = dateutil.parser.isoparse(
            query_results["result"][0]["timestamp"]
        )

        # Get covariates
        vnl = raster_client.get_zonal_stats(
            self.feature,
            get_raster_dataset("VNL"),
            stats="sum",
        )[0]["sum"]
        ghs_pop = raster_client.get_zonal_stats(
            self.feature,
            get_raster_dataset("GHS_POP_R2019A"),
            stats="sum",
        )[0]["sum"]
        area = await db_client.get_area_of_bpolys(self.feature.geometry)
        ghs_pop_density = ghs_pop / area
        data = {
            **get_smod_class_share(self.feature),
            "ghs_pop_density": ghs_pop_density,
            # TODO: Waiting for PR 266
            "ghs_pop": ghs_pop,
            "vnl": vnl,
            # "shdi": db_client.get_shdi(self.feature.geometry)
            "shdi": 0.5,
        }
        self.covariates = from_dict(data_class=Covariates, data=data)

    def calculate(self) -> None:
        directory = os.path.dirname(os.path.abspath(__file__))

        min_max_scaler = load_sklearn_model(os.path.join(directory, "scaler.joblib"))
        random_forest_regressor = load_sklearn_model(
            os.path.join(directory, "model.joblib")
        )

        cov = asdict(self.covariates)
        scaled = min_max_scaler.transform(
            [[v for k, v in cov.items() if k in ("ghs_pop", "ghs_pop_density", "vnl")]]
        )
        cov["ghs_pop"] = scaled[0][0]
        cov["ghs_pop_density"] = scaled[0][1]
        cov["vnl"] = scaled[0][2]

        self.building_area_prediction = random_forest_regressor.predict(
            [list(cov.values())]
        )[0]
        # Percentage mapped
        self.result.value = self.building_area_osm / self.building_area_prediction

        description = Template(self.metadata.result_description).substitute(
            building_area_osm=self.building_area_osm,
            building_area_prediction=self.building_area_prediction,
            percentage_mapped=self.result.value * 100,
        )
        # TODO: adjust percentage boundaries for green/yellow/red. Adjust in medata.yaml
        #       as well
        if 0.95 <= self.result.value:
            self.result.label = "green"
            self.result.description = (
                description + self.metadata.label_description["green"]
            )
        elif 0.75 <= self.result.value < 0.95:
            self.result.label = "yellow"
            self.result.description = (
                description + self.metadata.label_description["yellow"]
            )
        elif 0.0 <= self.result.value < 0.75:
            self.result.label = "red"
            self.result.description = (
                description + self.metadata.label_description["red"]
            )
        else:
            raise ValueError(
                "Result value (percentage mapped) is an unexpected value: {}".format(
                    self.result.value
                )
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


# TOOO: define self.model_name (see TODO above)
# TODO: check, whether raster containing no value and therefore indicator should be
#           undefined
# TODO: discuss & adjust percentage boundaries for green/yellow/red. Adjust values in
#           metadata.yaml as well(see TODO above)
# TODO: discuss: as the regressor is only trained with samples from africa, make it
#           usable for features in africa only?
