# -*- coding: utf-8 -*-
"""
Module providing the BokehJSONComparisonFixture class used in the bokeh_json_regression fixture
"""
from typing import Callable, Optional, TYPE_CHECKING, MutableSequence, MutableMapping, Set
from packaging.version import Version

import pytest

if TYPE_CHECKING:
    from pytest_regressions.data_regression import DataRegressionFixture
    from pytest_datadir import LazyDataDir

try:
    import bokeh

    BOKEH_VERSION = bokeh.__version__
    BOKEH_LT_3 = Version(BOKEH_VERSION) < Version("3.0.0")
except ImportError:
    BOKEH_VERSION = "unknown"
    BOKEH_LT_3 = False


def _clean_sequence(
    clean_fn: Callable, basic_clean_fn: Callable, sequence: MutableSequence, fp_precision: int
) -> MutableSequence:
    """
    Clean a mutable sequence

    :param clean_fn: function to call for dict entries in the sequence
    :param basic_clean_fn: function to call for entries that are not lists/tuples or dicts
    :param fp_precision: number of digits to use in floating point rounding
    """
    for index, entry in enumerate(sequence):
        if isinstance(entry, dict):
            sequence[index] = clean_fn(entry, fp_precision=fp_precision)
        elif isinstance(entry, (list, tuple)):
            sequence[index] = _clean_sequence(clean_fn, basic_clean_fn, list(entry), fp_precision=fp_precision)
        else:
            sequence[index] = basic_clean_fn(entry, fp_precision=fp_precision)

    return sequence


def _clean_bokeh_json_v3(data: MutableMapping, fp_precision: int) -> MutableMapping:
    """
    Clean JSON data produced by converting bokeh models to JSON in versions
    of bokeh of 3.0 or newer

    :param data: data to clean
    :param fp_precision: number of digits to use in floating point rounding
    """
    from bokeh.core.serialization import Buffer, Deserializer, Serializer
    import numpy as np
    import numbers

    def _clean_basic_entry_v3(entry, fp_precision):
        if isinstance(entry, Buffer):
            return entry.to_base64()
        if isinstance(entry, str):
            return str(entry)
        if isinstance(entry, numbers.Real) and not isinstance(entry, numbers.Integral):
            return round(float(entry), fp_precision)
        return entry

    if data.get("type") == "ndarray":
        array = Deserializer().deserialize(data)
        if array.dtype.char in np.typecodes["AllFloat"]:
            array = np.around(array, decimals=fp_precision)
            data = Serializer().serialize(array).content
    if data.get("type") == "typed_array" and data.get("dtype") in ("float32", "float64"):
        array = Deserializer().deserialize(data)
        array = np.around(array, decimals=fp_precision)
        data = Serializer().serialize(array).content

    # Remove IDs
    data = {key: val for key, val in data.items() if key not in ("id", "root_ids")}

    for key, val in data.items():
        if isinstance(val, dict):
            data[key] = _clean_bokeh_json_v3(val, fp_precision=fp_precision)
        elif isinstance(val, (list, tuple)):
            val = _clean_sequence(_clean_bokeh_json_v3, _clean_basic_entry_v3, list(val), fp_precision)
            # Filter out empty dictionaries
            while {} in val:
                val.remove({})
            data[key] = val
        else:
            data[key] = _clean_basic_entry_v3(val, fp_precision=fp_precision)

    # Filter out empty entries
    data = {key: val for key, val in data.items() if val not in (None, [], {})}

    return data


def _clean_bokeh_json_v2(data, fp_precision):
    """
    Clean JSON data produced by converting bokeh models to JSON in versions
    of bokeh of 3.0 or newer

    :param data: data to clean
    :param fp_precision: number of digits to use in floating point rounding
    """
    from bokeh.util.serialization import decode_base64_dict, encode_base64_dict  # pylint: disable=no-name-in-module
    import numpy as np

    def get_contained_keys(dict_val):
        keys = set(dict_val.keys())
        for val in dict_val.values():
            if isinstance(val, dict):
                keys = keys.union(get_contained_keys(val))

        return keys

    def get_normalized_order(dict_val, key_order, normed=None):
        if normed is None:
            normed = [(key, []) for key in key_order]
        for key, val in dict_val.items():
            index = key_order.index(key)
            if isinstance(val, dict):
                normed = get_normalized_order(val, key_order, normed=normed)
                normed[index][1].extend(sorted(val.keys()))
            else:
                if not isinstance(val, list):
                    val = [val]

                for v in val:
                    if isinstance(v, dict):
                        normed[index][1].extend(sorted(v.items()))
                    elif isinstance(v, (float, int)):
                        normed[index][1].append(str(v))
                    else:
                        normed[index][1].append(v)

        return normed

    def normalize_list_of_dicts(list_of_dicts: list[dict]) -> list[dict]:
        contained_keys: Set[str] = set()
        for data in list_of_dicts:
            contained_keys = contained_keys.union(get_contained_keys(data))
        contained_keys.discard("type")
        key_order = ["type"] + sorted(contained_keys)

        return sorted(list_of_dicts, key=lambda x: tuple(get_normalized_order(x, key_order)))

    def _clean_data_entry(entry, fp_precision):
        for key, val in entry.items():
            if "__ndarray__" in val:
                array = decode_base64_dict(val)
                array = np.around(array, decimals=fp_precision)
                entry[key] = encode_base64_dict(array)
            elif all(isinstance(x, int) for x in val):
                entry[key] = encode_base64_dict(np.array(val))
            elif all(isinstance(x, float) for x in val):
                entry[key] = encode_base64_dict(np.around(np.array(val), decimals=fp_precision))

        return entry

    data = {key: val for key, val in data.items() if key not in ("id", "root_ids")}

    for key, val in data.items():
        if isinstance(val, dict) and key == "data":
            data[key] = _clean_data_entry(val, fp_precision)
        elif isinstance(val, dict):
            data[key] = _clean_bokeh_json_v2(val, fp_precision=fp_precision)
        elif isinstance(val, (list, tuple)):
            val = _clean_sequence(_clean_bokeh_json_v2, lambda x, fp_precision: x, list(val), fp_precision)

            # Filter out empty dictionaries
            while {} in val:
                val.remove({})

            if all(isinstance(x, dict) for x in val):
                data[key] = normalize_list_of_dicts(val)
            else:
                data[key] = val
        elif isinstance(val, float):
            data[key] = round(val, fp_precision)
    data = {key: val for key, val in data.items() if val not in (None, [], {})}

    return data


if BOKEH_LT_3:
    default_json_clean_fn = _clean_bokeh_json_v2
else:
    default_json_clean_fn = _clean_bokeh_json_v3


class BokehJSONComparisonFixture:
    """
    Implementation of the bokeh_json_regression fixture
    """

    def __init__(
        self, data_regression: "LazyDataDir", request: pytest.FixtureRequest, clean_fn: Callable = default_json_clean_fn
    ) -> None:
        self.data_regression = data_regression
        self.request = request
        self.clean_fn = clean_fn

    def check_plot(
        self, model: "bokeh.models.Model", basename: Optional[str] = None, fp_precision: Optional[int] = None
    ) -> None:
        """
        Checks the given bokeh model against json data obtained from previous test runs using the data_regression
        fixture in the pytest-regressions plugin

        :param model: a bokeh model to check

        :param basename: basename of the file to test/record. If not given the name
            of the test is used.
            Use either `basename` or `fullpath`.

        :param fullpath: complete path to use as a reference file. This option
            will ignore ``lazy_datadir`` fixture when reading *expected* files but will still use it to
            write *obtained* files. Useful if a reference file is located in the session data dir for example.

        :param fp_precision: If given, round all floats in the dict to the given number of digits.

        ``basename`` and ``fullpath`` are exclusive.
        """
        __tracebackhide__ = True  # pylint: disable=unused-variable

        if BOKEH_LT_3:
            from bokeh.io import curdoc

            curdoc().clear()
            curdoc().add_root(model)
            json_to_check = curdoc().to_json()
        else:
            from bokeh.core.serialization import Serializer

            json_to_check = Serializer().serialize(model).content

        fp_precision = fp_precision or self.request.config.getoption("bokeh_fp_precision")

        json_to_check = self.clean_fn(json_to_check, fp_precision=fp_precision)

        # Remove bokeh version entry
        json_to_check.pop("version", None)

        self.data_regression.check(json_to_check, basename=basename)
