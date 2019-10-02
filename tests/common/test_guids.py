# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

import uuid

import pytest

from geocom.common.guids import Guid


def test_guid_bad():
    with pytest.raises(Guid.MissingGuidError):
        Guid()
    with pytest.raises(Guid.BadGuidError):
        Guid('test')


def test_guid_ok():
    assert Guid(uuid.UUID('b2ae10b1-a540-44b9-b785-7168f7d8d22e')) == '{B2AE10B1-A540-44B9-B785-7168F7D8D22E}'
    assert Guid('b2ae10b1-a540-44b9-b785-7168f7d8d22e') == '{b2ae10b1-a540-44b9-b785-7168f7d8d22e}'
    assert str(Guid('b2ae10b1a54044b9b7857168f7d8d22e')) == '{B2AE10B1-A540-44B9-B785-7168F7D8D22E}'
    assert str(Guid('{B2AE10B1-A540-44B9-B785-7168F7D8D22E}')) == '{B2AE10B1-A540-44B9-B785-7168F7D8D22E}'
    assert isinstance(Guid(allow_new=True), uuid.UUID) is True
    assert isinstance(Guid(None, True), uuid.UUID) is True
