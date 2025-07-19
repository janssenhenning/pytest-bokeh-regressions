# -*- coding: utf-8 -*-
"""
Pytest plugin for bokeh model regression testing
"""
import os
import warnings
from typing import Optional
from pathlib import Path
from packaging.version import Version


import pytest


def pytest_report_header():
    """
    Adds bokeh version to pytest header
    """
    import bokeh

    return [f"Bokeh: {bokeh.__version__}"]


def pytest_addoption(parser):
    """
    Add options for controlling the behaviour of the bokeh regression tests
    """
    group = parser.getgroup("bokeh regression tests")

    msg = "Show a comparison of the produced bokeh plots as html"
    group.addoption("--bokeh-html-comparison", action="store_true", help=msg)

    msg = "Compare the test files in subfolders named bokeh-<version> indicating the version used to produce the files"
    group.addoption("--bokeh-with-version", action="store_true", help=msg)

    msg = "If given no fallback version (the newest version older than the installed one) will be used if no test files are provided for the exact version"
    group.addoption("--bokeh-strict-version", action="store_true", help=msg)

    msg = "If given the test files are regenerated and put into the subfolder corresponding to the bokeh version used for the test"
    group.addoption("--bokeh-add-version", action="store_true", help=msg)

    msg = "Regenerate all test files produced by the bokeh regression fixtures"
    group.addoption("--bokeh-regen", action="store_true", help=msg)

    msg = "Default floating point precision used for rounding/hashing data entries appearing in the bokeh JSON data"
    group.addoption("--bokeh-fp-precision", default=5, type=int, help=msg)


@pytest.fixture
def bokeh_json_regression(
    request, bokeh_versioned_datadirs, lazy_datadir, original_datadir
):  # pylint:disable=redefined-outer-name
    """
    Fixture for regression tests of bokeh Models against data collected from previous test runs.
    Useful for testing visualization routines using the bokeh plotting framework.

    The fixture provides the ``check_plot`` method to which the bokeh model to test is passed.
    This is then converted to a JSON format by the corresponding bokeh routines, the gathered data
    is then 'cleaned' to make it usable for comparison against later test runs (removing IDs, rounding
    float values, sorting entries into a fixed order). The thus obtained dictionary is then compared using
    the ``data_regression`` fixture from the ``pytest-regressions``plugin.

    If the dicts are equal the test continues, otherwise an AssertionError is raised. To regenerate data for
    failed tests pass the --bokeh-regen flag to pytest.
    """
    from .json_comparison import BokehJSONComparisonFixture
    from pytest_regressions.data_regression import DataRegressionFixture

    if request.config.getoption("bokeh_with_version"):
        lazy_datadir, original_datadir = bokeh_versioned_datadirs

    data_regression = DataRegressionFixture(lazy_datadir, original_datadir, request)
    data_regression.force_regen = request.config.getoption("bokeh_regen") or request.config.getoption(
        "bokeh_add_version"
    )

    return BokehJSONComparisonFixture(data_regression, request)


def _get_fallback_version(current_version: str, datadir: Path) -> Optional[str]:
    """
    Get the newest available bokeh version older than the current version
    for which test files exist in the corresponding data directory

    :param current_version: string of the current version of the bokeh package
    :param datadir: Path to the directory to search for test files
    """
    fallback_version = Version("0.0.0")

    for f in os.scandir(datadir):
        if f.is_dir() and f.name.startswith("bokeh-"):
            _, _, version = f.name.partition("-")
            version = Version(version)
            if fallback_version < version <= Version(current_version):
                fallback_version = version
    if fallback_version != Version("0.0.0"):
        return str(fallback_version)
    return None


@pytest.fixture
def bokeh_versioned_datadirs(lazy_datadir, original_datadir, request):
    """
    Fixture to provide paths to test files for bokeh regression tests, which
    include subfolders declaring the used bokeh version for generating the contained test files.
    This fixture is only used when the --bokeh-with-version flag is used

    The logic here is as follows. The test files are searched for staring from the datadir provided
    by the pytest-datadir plugin. If a subfolder named bokeh-<current-version> exists this is used.
    If this is not the case there are three different options
        1. If a subfolder corresponding to an older version of bokeh is present and the
           --bokeh-strict-version flag is not present the tests will be run against the files
           corresponding to the newest (but older than the current) version of bokeh
        2. If a subfolder corresponding to an older version of bokeh is present and the
           --bokeh-strict-version flag is present the tests will not be run against older versions
           and thus generate test files for the current version
        2. If --bokeh-add-version flag the tests will be run generating test files in the subfolder
           corresponding to the current bokeh version
    """
    import bokeh

    test_file_version = bokeh.__version__
    folder_name = f"bokeh-{test_file_version}"

    if (original_datadir / folder_name).is_dir() and request.config.getoption("bokeh_add_version"):
        warnings.warn(
            f"The --bokeh-add-version flag was given but the test files for the current version ({test_file_version})"
            "are already available. The test files will be regenerated in this test run"
        )

    if (
        not (original_datadir / folder_name).is_dir()
        and not request.config.getoption("bokeh_strict_version")
        and not request.config.getoption("bokeh_add_version")
    ):
        fallback_version = _get_fallback_version(test_file_version, original_datadir)
        if fallback_version is not None:
            test_file_version = fallback_version
            folder_name = f"bokeh-{test_file_version}"

    return lazy_datadir / f"bokeh-{test_file_version}", original_datadir / f"bokeh-{test_file_version}"
