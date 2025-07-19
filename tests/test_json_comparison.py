# -*- coding: utf-8 -*-
"""
Tests of the bokeh_json_regression fixture
"""
from packaging.version import Version

import pytest
import bokeh
from bokeh.plotting import figure

BOKEH_VERSION = bokeh.__version__
BOKEH_LT_3 = Version(BOKEH_VERSION) < Version("3.0.0")

bokehv3_test = pytest.mark.skipif(BOKEH_LT_3, reason="Test for bokeh version 3 or newer")
bokehv2_test = pytest.mark.skipif(not BOKEH_LT_3, reason="Test for bokeh version 2 or older")


@bokehv3_test
def test_example(bokeh_json_regression):
    """
    Minimal test of the fixture
    """
    x = [1, 3, 6, 4, 9]
    y = [0, 2, 7, 5, 3]

    p = figure(title="Minimal Example", x_axis_label="x", y_axis_label="y")
    p.line(x, y, line_width=2)

    bokeh_json_regression.check_plot(p)


@bokehv2_test
def test_example_v2(bokeh_json_regression):
    """
    Minimal test of the fixture testing against files expected for bokeh version 2 or older
    """
    x = [1, 3, 6, 4, 9]
    y = [0, 2, 7, 5, 3]

    p = figure(title="Minimal Example", x_axis_label="x", y_axis_label="y")
    p.line(x, y, line_width=2)

    bokeh_json_regression.check_plot(p)


@bokehv3_test
def test_basename(bokeh_json_regression):
    """
    Tests of the fixture when passing an explicit basename argument
    """
    x = [1, 3, 6, 4, 9]
    y = [0, 2, 7, 5, 3]

    p = figure(title="Minimal Example", x_axis_label="x", y_axis_label="y")
    p.line(x, y, line_width=2)

    bokeh_json_regression.check_plot(p, basename="changed.basename")


def test_fp_precision(bokeh_json_regression):
    """
    Test of the fp_precision argument
    """
    x = [1.2345, 2.34567]
    y = [3.4567, 4.56789]

    p = figure(title="Minimal Example with float values", x_axis_label="x", y_axis_label="y")
    p.line(x, y, line_width=2)

    basename = f"test_fp_precision{'_v2' if BOKEH_LT_3 else ''}"
    bokeh_json_regression.check_plot(p, fp_precision=2, basename=basename)

    with pytest.raises(AssertionError):
        x = [1.24567, 2.45678]
        y = [3.4567, 4.56789]

        p = figure(title="Minimal Example with float values", x_axis_label="x", y_axis_label="y")
        p.line(x, y, line_width=2)

        bokeh_json_regression.check_plot(p, fp_precision=2, basename=basename)


def test_array(bokeh_json_regression):
    """
    Test of the fixture when the JSON data contains numpy array data
    """
    import numpy as np

    x = np.linspace(-1, 1, 100)
    y = x**2

    p = figure(title="Parabola", x_axis_label="x", y_axis_label="y")
    p.line(x, y, line_width=2)

    basename = f"test_array{'_v2' if BOKEH_LT_3 else ''}"
    bokeh_json_regression.check_plot(p, basename=basename)


def test_array_fp_precision(bokeh_json_regression):
    """
    Test of the fixture when the JSON data contains numpy array data and an fp_precision argument is passed
    """
    import numpy as np

    x = np.linspace(-1, 1, 100)
    y = x**2

    p = figure(title="Parabola", x_axis_label="x", y_axis_label="y")
    p.line(x, y, line_width=2)

    basename = f"test_array_fp_precision{'_v2' if BOKEH_LT_3 else ''}"
    bokeh_json_regression.check_plot(p, fp_precision=2, basename=basename)

    with pytest.raises(AssertionError):
        x = x + 0.01
        y = y - 0.01

        p = figure(title="Parabola", x_axis_label="x", y_axis_label="y")
        p.line(x, y, line_width=2)

        bokeh_json_regression.check_plot(p, fp_precision=2, basename=basename)
