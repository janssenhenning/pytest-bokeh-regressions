# -*- coding: utf-8 -*-
"""
Tests of the pytest plugin when using the --bokeh-with-version flag in different configurations
"""
import shutil
from pathlib import Path
from packaging.version import Version
import pytest

import bokeh

BOKEH_VERSION = bokeh.__version__
BOKEH_LT_3 = Version(BOKEH_VERSION) < Version("3.0.0")
BOKEH_FALLBACK_TEST_VERSION = "0.0.1"


@pytest.mark.parametrize(
    "cli, bokeh_version, success_expected",
    [
        (None, BOKEH_VERSION, True),
        (None, BOKEH_FALLBACK_TEST_VERSION, True),
        ("--bokeh-strict-version", BOKEH_VERSION, True),
        ("--bokeh-strict-version", BOKEH_FALLBACK_TEST_VERSION, False),
    ],
)
def test_example_version(pytester, cli, bokeh_version, success_expected):
    """
    Tests of the versioning feature of the plugin.

    Tests that the test files are searched for in the correct place or the tests fail
    if
        - the current version has test files available (with and without the --bokeh-strict-version flag)
        - there is an older version available (fallback to these test files only if the --bokeh-strict-version is not present)
    """

    path = pytester.path / "test_example_version" / f"bokeh-{bokeh_version}"
    path.mkdir(parents=True)

    test_file_name = "test_example_v2.yml" if BOKEH_LT_3 else "test_example.yml"

    shutil.copyfile(Path(__file__).parent / "test_json_comparison" / test_file_name, path / "test_example.yml")

    pytester.makepyfile(
        """
    from bokeh.plotting import figure

    def test_example(bokeh_json_regression):
        x = [1,3,6,4,9]
        y = [0,2,7,5,3]

        p = figure(title="Minimal Example", x_axis_label='x', y_axis_label='y')
        p.line(x,y,line_width=2)

        bokeh_json_regression.check_plot(p)
    """
    )

    if cli is None:
        cli = ""
    result = pytester.runpytest("--bokeh-with-version", cli)

    if success_expected:
        result.assert_outcomes(passed=1)
    else:
        result.assert_outcomes(failed=1)


@pytest.mark.parametrize(
    "cli, bokeh_version",
    [
        (None, BOKEH_VERSION),
        (None, BOKEH_FALLBACK_TEST_VERSION),
        ("--bokeh-strict-version", BOKEH_VERSION),
        ("--bokeh-strict-version", BOKEH_FALLBACK_TEST_VERSION),
    ],
)
def test_add_version(pytester, cli, bokeh_version):
    """
    Tests of the --bokeh-add-version flag

    Ensuring that the files are generated if the versions do not match up
    and a warning is shown if the flag is given but test files for the current version exist
    """

    path = pytester.path / "test_add_version" / f"bokeh-{bokeh_version}"
    path.mkdir(parents=True)

    test_file_name = "test_example_v2.yml" if BOKEH_LT_3 else "test_example.yml"

    shutil.copyfile(Path(__file__).parent / "test_json_comparison" / test_file_name, path / "test_example.yml")

    pytester.makepyfile(
        """
    from bokeh.plotting import figure

    def test_example(bokeh_json_regression):
        x = [1,3,6,4,9]
        y = [0,2,7,5,3]

        p = figure(title="Minimal Example", x_axis_label='x', y_axis_label='y')
        p.line(x,y,line_width=2)

        bokeh_json_regression.check_plot(p)
    """
    )

    if cli is None:
        cli = "--bokeh-add-version"
    result = pytester.runpytest("--bokeh-with-version", "--bokeh-add-version", cli)

    if BOKEH_VERSION == bokeh_version:
        result.stdout.re_match_lines([".*UserWarning: .*The --bokeh-add-version flag was given but the test files.*"])
        result.assert_outcomes(passed=1)
    else:
        result.assert_outcomes(failed=1)

    assert (pytester.path / "test_add_version" / f"bokeh-{BOKEH_VERSION}" / "test_example.yml").exists()
