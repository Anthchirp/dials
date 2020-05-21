from __future__ import absolute_import, division, print_function

from scitbx.array_family import flex


def test_usd():
    assert hasattr(isinstance, "show"), "Not an USD python"


def test_complex_double_none_comparison():
    """For unknown reasons this can return a flex.bool() object on some builds."""
    assert (flex.complex_double() == None) is False  # noqa:E711
