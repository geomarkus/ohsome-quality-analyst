"""Global Variables and Functions."""

import glob
import logging
import os
from typing import Dict, List

import yaml

from ohsome_quality_analyst.config.config import get_config
from ohsome_quality_analyst.utils.helper import flatten_sequence, get_module_dir

CONFIG = get_config()
DATASETS = CONFIG["datasets"]
OHSOME_API = CONFIG["ohsome_api"]
GEOM_SIZE_LIMIT = CONFIG["geom_size_limit"]
USER_AGENT = CONFIG["user_agent"]

# Possible indicator layer combinations
INDICATOR_LAYER = (
    ("GhsPopComparisonBuildings", "building_count"),
    ("GhsPopComparisonRoads", "jrc_road_length"),
    ("GhsPopComparisonRoads", "major_roads_length"),
    ("MappingSaturation", "building_count"),
    ("MappingSaturation", "major_roads_length"),
    ("MappingSaturation", "amenities"),
    ("MappingSaturation", "jrc_health_count"),
    ("MappingSaturation", "jrc_mass_gathering_sites_count"),
    ("MappingSaturation", "jrc_railway_length"),
    ("MappingSaturation", "jrc_road_length"),
    ("MappingSaturation", "jrc_education_count"),
    ("MappingSaturation", "mapaction_settlements_count"),
    ("MappingSaturation", "mapaction_major_roads_length"),
    ("MappingSaturation", "mapaction_rail_length"),
    ("MappingSaturation", "mapaction_lakes_area"),
    ("MappingSaturation", "mapaction_rivers_length"),
    ("MappingSaturation", "ideal_vgi_infrastructure"),
    ("MappingSaturation", "ideal_vgi_poi"),
    ("Currentness", "major_roads_count"),
    ("Currentness", "building_count"),
    ("Currentness", "amenities"),
    ("Currentness", "jrc_health_count"),
    ("Currentness", "jrc_education_count"),
    ("Currentness", "jrc_road_count"),
    ("Currentness", "jrc_railway_count"),
    ("Currentness", "jrc_airport_count"),
    ("Currentness", "jrc_water_treatment_plant_count"),
    ("Currentness", "jrc_power_generation_plant_count"),
    ("Currentness", "jrc_cultural_heritage_site_count"),
    ("Currentness", "jrc_bridge_count"),
    ("Currentness", "jrc_mass_gathering_sites_count"),
    ("Currentness", "mapaction_settlements_count"),
    ("Currentness", "mapaction_major_roads_length"),
    ("Currentness", "mapaction_rail_length"),
    ("Currentness", "mapaction_lakes_count"),
    ("Currentness", "mapaction_rivers_length"),
    ("PoiDensity", "poi"),
    ("TagsRatio", "jrc_health_count"),
    ("TagsRatio", "jrc_education_count"),
    ("TagsRatio", "jrc_road_length"),
    ("TagsRatio", "jrc_airport_count"),
    ("TagsRatio", "jrc_power_generation_plant_count"),
    ("TagsRatio", "jrc_cultural_heritage_site_count"),
    ("TagsRatio", "jrc_bridge_count"),
    ("TagsRatio", "jrc_mass_gathering_sites_count"),
)


def load_metadata(module_name: str) -> Dict:
    """
    Read metadata of all indicators or reports from YAML files.

    Those text files are located in the directory of each indicator/report.

    Args:
        module_name: Either indicators or reports.
    Returns:
        A Dict with the class names of the indicators/reports
        as keys and metadata as values.
    """
    if module_name != "indicators" and module_name != "reports":
        raise ValueError("module name value can only be 'indicators' or 'reports'.")

    directory = get_module_dir("ohsome_quality_analyst.{0}".format(module_name))
    files = glob.glob(directory + "/**/metadata.yaml", recursive=True)
    metadata = {}
    for file in files:
        with open(file, "r") as f:
            metadata = {**metadata, **yaml.safe_load(f)}  # Merge dicts
    return metadata


def get_metadata(module_name: str, class_name: str) -> Dict:
    """Get metadata of an indicator or report based on its class name.

    This is implemented outside the metadata class to be able to
    access metadata of all indicators/reports without instantiation of those.

    Args:
        module_name: Either indicators or reports.
        class_name: Any class name in Camel Case which is implemented
                    as report or indicator
    """
    if module_name != "indicators" and module_name != "reports":
        raise ValueError("module name value can only be 'indicators' or 'reports'.")

    metadata = load_metadata(module_name)
    try:
        return metadata[class_name]
    except KeyError:
        logging.error(
            "Invalid {0} class name. Valid {0} class names are: ".format(
                module_name[:-1]
            )
            + str(metadata.keys())
        )
        raise


def load_layer_definitions() -> Dict:
    """
    Read ohsome API parameters of all layer from YAML file.

    Returns:
        A Dict with the layer names of the layers as keys.
    """
    directory = get_module_dir("ohsome_quality_analyst.ohsome")
    file = os.path.join(directory, "layer_definitions.yaml")
    with open(file, "r") as f:
        return yaml.safe_load(f)


def get_layer_definition(layer_name: str) -> Dict:
    """
    Get ohsome API parameters of a single layer based on layer name.

    This is implemented outside the layer class to
    be able to access layer definitions of all indicators without
    instantiation of those.
    """
    layers = load_layer_definitions()
    try:
        return layers[layer_name]
    except KeyError:
        logging.error(
            "Invalid layer name. Valid layer names are: " + str(layers.keys())
        )
        raise


def get_indicator_classes() -> Dict:
    """Map indicator name to corresponding class"""
    raise NotImplementedError(
        "Use utils.definitions.load_indicator_metadata() and"
        + "utils.helper.name_to_class() instead"
    )


def get_report_classes() -> Dict:
    """Map report name to corresponding class."""
    raise NotImplementedError(
        "Use utils.definitions.load_indicator_metadata() and"
        + "utils.helper.name_to_class() instead"
    )


def get_indicator_names() -> List[str]:
    return list(load_metadata("indicators").keys())


def get_report_names() -> List[str]:
    return list(load_metadata("reports").keys())


def get_layer_names() -> List[str]:
    return list(load_layer_definitions().keys())


def get_dataset_names() -> List[str]:
    return list(DATASETS.keys())


def get_fid_fields() -> List[str]:
    return flatten_sequence(DATASETS)


# def get_dataset_names_api() -> List[str]:
#     return list(DATASETS_API.keys())

# def get_fid_fields_api() -> List[str]:
#     return flatten_sequence(DATASETS_API)
