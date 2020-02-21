# coding: utf-8
#
# Copyright 2019 Geocom Informatik AG / VertiGIS

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import pytest

import gpf.paths as paths


# noinspection PyTypeChecker
def test_explode():
    with pytest.raises(TypeError):
        paths.explode(None)
        paths.explode(1)
    assert paths.explode(r'C:/temp/test.gdb') == ('C:\\temp', 'test', '.gdb')
    assert paths.explode(r'C:/temp/folder') == ('C:\\temp', 'folder', '')


# noinspection PyTypeChecker
def test_normalize():
    with pytest.raises(TypeError):
        paths.normalize(None)
        paths.normalize(1)
    assert paths.normalize(r'A/B\C') == 'a\\b\\c'
    assert paths.normalize(r'A/b\c', False) == 'A\\b\\c'


# noinspection PyTypeChecker
def test_join():
    with pytest.raises(TypeError):
        paths.concat()
        paths.concat(None)
        paths.concat(1, 2, 3)
    assert paths.concat('a', 'b', 'c') == 'a\\b\\c'


def test_unqualify():
    assert paths.unqualify(r'C:/test/bla.gdb/ele/ele_kabel') == 'ele_kabel'
    assert paths.unqualify(r'C:/test/bla.sde/user.ele/user.ele_kabel') == 'ele_kabel'
    assert paths.unqualify(r'C:/test/bla.sde/schema.dbo.ele/schema.dbo.ele_kabel') == 'ele_kabel'


# noinspection PyTypeChecker
def test_getabs():
    with pytest.raises(TypeError):
        paths.get_abs(None)
        paths.get_abs(1)
        paths.get_abs('test', 2)
    curdir = os.path.dirname(__file__)
    # inspect.getabsfile() returns lower case
    assert paths.get_abs('test.txt') == os.path.join(curdir, 'test.txt').lower()
    assert paths.get_abs('test.txt', os.path.dirname(curdir)) == os.path.join(os.path.dirname(curdir), 'test.txt')
    assert paths.get_abs(__file__) == os.path.normpath(__file__)


# noinspection PyTypeChecker
def test_findparent():
    with pytest.raises(TypeError):
        paths.find_parent(None, None)
        paths.find_parent(1, 2)
    test_dir = 'C:\\Projects\\parent\\LEVEL0\\level1\\level2.txt'
    assert paths.find_parent(test_dir, 'level0') == 'C:\\Projects\\parent'
    assert paths.find_parent(test_dir, 'LEVEL0') == 'C:\\Projects\\parent'
    assert paths.find_parent(test_dir, 'Level') == ''
    assert paths.find_parent(test_dir, 'c:') == ''
    assert paths.find_parent(test_dir, '?') == ''


def test_path_bad_init():
    with pytest.raises(TypeError):
        paths.Path(None)
        paths.Path('')
    with pytest.raises(ValueError):
        paths.Path(r'C:\directory\file.ext', r'C:\directory')


def test_path_bad_file():
    pm = paths.Path(r'C:\directory\file.ext')
    assert not pm.is_file
    assert not pm.is_dir
    assert not pm.exists
    assert pm.extension() == '.ext'
    assert pm.extension(False) == 'ext'
    assert pm.basename() == 'file.ext'
    assert pm.basename(False) == 'file'
    assert pm.make_path('sub1', 'sub2') == 'C:\\directory\\sub1\\sub2\\file.ext'


def test_path_bad_dir():
    pm = paths.Path(r'C:\directory\test')
    assert not pm.is_file
    assert not pm.is_dir
    assert not pm.exists
    assert pm.extension() == ''
    assert pm.extension(False) == ''
    assert pm.basename() == 'test'
    assert pm.basename(False) == 'test'
    assert pm.make_path('sub1', 'sub2') == 'C:\\directory\\test\\sub1\\sub2'


def test_path_good_file():
    file_name = os.path.basename(__file__)
    dir_path = os.path.dirname(__file__)
    pm = paths.Path(__file__)
    assert pm.is_file
    assert not pm.is_dir
    assert pm.exists
    assert pm.extension() == '.py'
    assert pm.extension(False) == 'py'
    assert pm.basename() == file_name
    assert pm.basename(False) == file_name.split('.')[0]
    assert pm.make_path('sub1', 'sub2') == os.path.join(dir_path, 'sub1', 'sub2', file_name)


def test_path_good_dir():
    dir_path = os.path.dirname(__file__)
    dir_name = os.path.basename(dir_path)
    pm = paths.Path(dir_path)
    assert not pm.is_file
    assert pm.is_dir
    assert pm.exists
    assert pm.extension() == ''
    assert pm.extension(False) == ''
    assert pm.basename() == dir_name
    assert pm.basename(False) == dir_name
    assert pm.make_path('sub1', 'sub2') == os.path.join(dir_path, 'sub1', 'sub2')


def test_getworkspace():
    assert paths.get_workspace('C:\\temp\\test.gdb\\feature_dataset\\feature_class') == \
           paths.Workspace('C:\\temp\\test.gdb\\feature_dataset')
    assert paths.get_workspace(
            'C:\\temp\\test.gdb\\feature_dataset\\feature_class', True) == paths.Workspace('C:\\temp\\test.gdb')


def test_isgdbpath():
    assert paths.split_gdbpath('C:\\folder\\test.gdb\\q.fds\\q.fc') == ('C:\\folder\\test.gdb', 'fds', 'fc')
    assert paths.split_gdbpath('C:\\test.sde\\q.fds\\q.fc', False) == ('C:\\test.sde', 'q.fds', 'q.fc')
    with pytest.raises(ValueError):
        paths.split_gdbpath('C:\\test.gdb\\folder\\test2.gdb\\subfolder')
        paths.split_gdbpath('C:\\test.gdb\\a\\b\\c')


def test_workspace_gdb():
    ws = paths.Workspace('test.gdb', qualifier='TEST', base='C:\\temp', separator='|')
    assert ws.root == paths.Workspace('C:\\temp\\test.gdb')
    assert ws.qualifier == ''
    assert ws.separator == ''
    assert ws.make_path('test_table') == 'C:\\temp\\test.gdb\\test_table'
    assert ws.make_path('', 'root_fc') == 'C:\\temp\\test.gdb\\root_fc'
    assert ws.make_path('ele', 'ele_kabel') == 'C:\\temp\\test.gdb\\ele\\ele_kabel'
    ws = paths.Workspace('C:\\temp\\test.gdb')
    assert not ws.exists
    assert ws.root == paths.Workspace('C:\\temp\\test.gdb')
    assert ws.get_parent(str(ws)) == 'C:\\temp\\test.gdb'
    assert ws.get_parent(str(ws), True) == 'C:\\temp'
    assert ws.get_root(str(ws)) == 'C:\\temp\\test.gdb'
    assert ws.is_gdb is True
    assert ws.qualifier == ''
    assert ws.separator == ''
    assert ws.qualify('test', 'my_qualifier') == 'test'
    with pytest.raises(ValueError):
        ws.qualify('')
    assert ws.make_path('ele', 'ele_kabel') == 'C:\\temp\\test.gdb\\ele\\ele_kabel'
    with pytest.raises(IndexError):
        ws.make_path('p1', 'p2', 'p3')
    assert paths.Workspace.get_root('C:\\temp\\test.shp') == 'C:\\temp'
    assert paths.Workspace.get_parent('C:\\temp\\test.shp') == 'C:\\temp'
    assert ws.get_root('C:\\temp\\test.gdb\\ele\\ele_kabel') == 'C:\\temp\\test.gdb'


def test_workspace_mem():
    ws = paths.Workspace('in_memory')
    assert ws.root == paths.Workspace('in_memory')
    assert ws.qualifier == ''
    assert ws.separator == ''
    assert ws.make_path('ele', 'ele_kabel') == 'in_memory\\ele\\ele_kabel'
    assert paths.Workspace.get_parent(str(ws)) == 'in_memory'
    assert paths.Workspace.get_parent(str(ws), True) == 'in_memory'
    assert ws.get_root(str(ws)) == 'in_memory'
    assert ws.is_gdb is True
