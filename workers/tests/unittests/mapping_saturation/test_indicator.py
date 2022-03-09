import asyncio
import os
import unittest
from unittest.mock import MagicMock, Mock, patch

from ohsome_quality_analyst.indicators.mapping_saturation.indicator import (
    MappingSaturation,
    validate_query_results,
)
from ohsome_quality_analyst.utils.exceptions import LayerDataSchemaError
from tests.unittests.utils import get_geojson_fixture


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class TestIndicatorMappingSaturation(unittest.TestCase):
    def setUp(self):
        self.feature = get_geojson_fixture("heidelberg-altstadt-feature.geojson")

    @patch(
        "ohsome_quality_analyst.ohsome.client.query",
        new_callable=AsyncMock,
        return_value={},
    )
    def test_preprocess_osm_data_schema_invalid(self, mock):
        """Test validation process of the ohsome API data."""
        indicator = MappingSaturation(layer=Mock(), feature=Mock())

        with self.assertRaises(LayerDataSchemaError):
            asyncio.run(indicator.preprocess())

    @patch(
        "ohsome_quality_analyst.ohsome.client.query",
        new_callable=AsyncMock,
    )
    def test_preprocess_osm_data_schema_valid(self, mock):
        """Test validation process of the ohsome API data."""
        fixtures_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "fixtures"
        )

        fixture = os.path.join(fixtures_dir, "ohsome-response-200-valid.geojson")
        with open(fixture, "r") as reader:
            mock.return_value = reader.read()

        indicator = MappingSaturation(layer=Mock(), feature=Mock())
        with self.assertRaises(LayerDataSchemaError):
            asyncio.run(indicator.preprocess())

    def test_validate_query_results(self):
        validate_query_results(
            {"result": [{"value": 1.0, "timestamp": "2020-03-20T01:30:08.180856"}]}
        )

    def test_validate_query_results_invalid(self):
        with self.assertRaises(LayerDataSchemaError):
            validate_query_results({})
        with self.assertRaises(LayerDataSchemaError):
            validate_query_results(
                {"result": [{"value": 1.0}]}  # Missing timestamp item
            )


if __name__ == "__main__":
    unittest.main()
