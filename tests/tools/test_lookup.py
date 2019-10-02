# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

from geocom.tools.lookup import coord_key


def test_coord_key():
    coord = (4.2452, 23.24541)
    assert coord_key(*coord) == (42451, 232454)
    assert coord_key(53546343.334242254, 23542233.354352246) == (535463433342, 235422333543)
    assert coord_key(1, 2, 3) == (10000, 20000, 30000)
