import unittest

from schema import Schema

from ohsome_quality_analyst.ohsome import client

from .utils import get_geojson_fixture, oqt_vcr



class TestOhsomeClient(unittest.TestCase):
    def test_get_latest_ohsome_timestamp():
        client.get_latest_ohsome_timestamp()


class TestOhsomeClientQuery(unittest.TestCase):
    def setUp(self):
        self.feature = get_geojson_fixture("heidelberg-altstadt-feature.geojson")
        self.feature_collection = get_geojson_fixture(
            "heidelberg-bahnstadt-bergheim-featurecollection.geojson"
        )
        self.layer = None
        self.time = "2008-01-01//P1M"

        self.schema = Schema(
            {"result": [{"value": float, "timestamp": str}]},
            ignore_extra_keys=True,
        )
        self.schema_group_by = Schema(
            {"result": [{"value": float, "timestamp": str}]},
            ignore_extra_keys=True,
        )

    @oqt_vcr.use_cassette()
    def test_layer_feature(self):
        result = client.query(self.layer, self.feature)
        self.assertTrue(self.schema.is_valid(result))

    @oqt_vcr.use_cassette()
    def test_layer_feature_time(self):
        result = client.query(self.layer, self.feature, self.time)
        self.assertTrue(self.schema.is_valid(result))

    @oqt_vcr.use_cassette()
    def test_layer_feature_collection(self):
        """Test groupBy boundary query."""
        result = client.query(self.layer, self.feature_collection)
        self.assertTrue(self.schema_group_by.is_valid(result))

    @oqt_vcr.use_cassette()
    def test_layer_feature_collection_time(self):
        """Test groupBy boundary query."""
        result = client.query(self.layer, self.feature_collection, self.time)
        self.assertTrue(self.schema_group_by.is_valid(result))

    @oqt_vcr.use_cassette()
    def test_custom(self):
        endpoint = "elements/area"
        filter_ = "building=* and geometry:polygon"
        url = ""
        data = ""
        result = client.query_ohsome_api(url, data)
        self.assertTrue(self.schema.is_valid(result))

    @oqt_vcr.use_cassette()
    def test_custom_ratio(self):
        endpoint = "elements/count/ratio"
        filter_ = "power=plant"
        filter2 = "power=plant and power=* and name=*"
        url = ""
        data = ""
        result = client.query_ohsome_api(url, data)
