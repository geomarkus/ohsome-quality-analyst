import asyncio
import unittest
from datetime import datetime

from geojson import FeatureCollection

from ohsome_quality_analyst.geodatabase import client as db_client
from ohsome_quality_analyst.indicators.building_area.indicator import (
    BuildingArea,
    get_smod_class_share,
    select_hex_cells,
)

from .utils import oqt_vcr


class TestIndicatorBuildingArea(unittest.TestCase):
    def setUp(self):
        # Touggourt, Algeria
        self.feature = asyncio.run(
            db_client.get_feature_from_db(dataset="regions", feature_id="12")
        )
        self.layer_name = "building_area"
        self.indicator = BuildingArea(feature=self.feature, layer_name=self.layer_name)

    @oqt_vcr.use_cassette()
    def test_indicator(self):
        asyncio.run(self.indicator.preprocess())
        self.assertIsNotNone(self.indicator.building_area_osm)
        self.assertIsInstance(self.indicator.building_area_osm, list)
        self.assertGreater(len(self.indicator.building_area_osm), 0)
        self.assertIsInstance(self.indicator.result.timestamp_osm, list)
        self.assertIsInstance(self.indicator.result.timestamp_osm[0], datetime)
        self.assertIsInstance(self.indicator.result.timestamp_oqt, datetime)
        self.assertIsNotNone(self.indicator.result.timestamp_oqt)
        self.assertIsNotNone(self.indicator.covariates)
        self.assertGreater(len(self.indicator.covariates), 0)
        self.assertIsNotNone(self.indicator.covariates[0].ghs_pop)
        self.assertIsNotNone(self.indicator.covariates[0].ghs_pop_density)
        self.assertIsNotNone(self.indicator.covariates[0].water)
        self.assertIsNotNone(self.indicator.covariates[0].very_low_density_rural)
        self.assertIsNotNone(self.indicator.covariates[0].low_density_rural)
        self.assertIsNotNone(self.indicator.covariates[0].rural_cluster)
        self.assertIsNotNone(self.indicator.covariates[0].suburban_or_peri_urban)
        self.assertIsNotNone(self.indicator.covariates[0].semi_dense_urban_cluster)
        self.assertIsNotNone(self.indicator.covariates[0].dense_urban_cluster)
        self.assertIsNotNone(self.indicator.covariates[0].urban_centre)
        self.assertIsNotNone(self.indicator.covariates[0].shdi)
        self.assertIsNotNone(self.indicator.covariates[0].vnl)
        self.assertLessEqual(self.indicator.covariates[0].urban_centre, 1)
        self.assertGreaterEqual(self.indicator.covariates[0].urban_centre, 0)
        self.assertGreater(
            (
                self.indicator.covariates[0].urban_centre
                + self.indicator.covariates[0].dense_urban_cluster
                + self.indicator.covariates[0].semi_dense_urban_cluster
                + self.indicator.covariates[0].suburban_or_peri_urban
                + self.indicator.covariates[0].rural_cluster
                + self.indicator.covariates[0].low_density_rural
                + self.indicator.covariates[0].very_low_density_rural
                + self.indicator.covariates[0].water
            ),
            0,
        )
        self.assertRaises(
            AttributeError, lambda: self.indicator.covariates[0].some_random_key
        )

        self.indicator.calculate()
        self.assertIsNotNone(self.indicator.result.label)
        self.assertIsNotNone(self.indicator.result.value)
        self.assertIsNotNone(self.indicator.result.description)
        self.assertLessEqual(self.indicator.result.value, 1.0)
        self.assertGreaterEqual(self.indicator.result.value, 0.0)

        self.indicator.create_figure()
        self.assertIsNotNone(self.indicator.result.svg)

    def test_get_smod_class_share(self):
        self.feature = asyncio.run(
            db_client.get_feature_from_db(dataset="regions", feature_id="3")
        )
        result = get_smod_class_share(self.feature)
        self.assertDictEqual(result, {"urban_centre": 1.0})

    def test_select_hex_cells(self):
        # TODO: Add fid 12 to test regions in DB
        self.feature = asyncio.run(
            db_client.get_feature_from_db(dataset="regions", feature_id="12")
        )
        result = asyncio.run(select_hex_cells(self.feature.geometry))
        self.assertIsInstance(result, FeatureCollection)
        self.assertIsNotNone(result.features)


if __name__ == "__main__":
    unittest.main()
