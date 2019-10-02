# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

import os

import pytest

import geocom.common.paths as paths


def test_explode():
    assert paths.explode(r'C:/temp/test.gdb') == ('C:\\temp', 'test', '.gdb')
    assert paths.explode(r'C:/temp/folder') == ('C:\\temp', 'folder', '')


def test_normalize():
    assert paths.normalize(r'A/B\C') == 'a\\b\\c'
    assert paths.normalize(r'A/b\c', False) == 'A\\b\\c'


def test_join():
    assert paths.join('a', 'b', 'c') == 'a\\b\\c'


def get_abs():
    curdir = os.path.dirname(__file__)
    assert paths.get_abs('test.txt') == os.path.join(curdir, 'test.txt')
    assert paths.get_abs('test.txt', os.path.dirname(curdir)) == os.path.join(os.path.dirname(curdir), 'test.txt')
    assert paths.get_abs(__file__) == os.path.normpath(__file__)


# noinspection PyTypeChecker
def test_pathmanager_bad_init():
    with pytest.raises(TypeError):
        paths.PathManager(None)
        paths.PathManager('')
    with pytest.raises(ValueError):
        paths.PathManager(r'C:\directory\file.ext', r'C:\directory')


def test_pathmanager_bad_file():
    pm = paths.PathManager(r'C:\directory\file.ext')
    assert not pm.is_file
    assert not pm.is_dir
    assert not pm.exists
    assert pm.extension() == '.ext'
    assert pm.extension(False) == 'ext'
    assert pm.basename() == 'file.ext'
    assert pm.basename(False) == 'file'
    assert pm.construct('sub1', 'sub2') == 'C:\\directory\\sub1\\sub2\\file.ext'


def test_pathmanager_bad_dir():
    pm = paths.PathManager(r'C:\directory\test')
    assert not pm.is_file
    assert not pm.is_dir
    assert not pm.exists
    assert pm.extension() == ''
    assert pm.extension(False) == ''
    assert pm.basename() == 'test'
    assert pm.basename(False) == 'test'
    assert pm.construct('sub1', 'sub2') == 'C:\\directory\\test\\sub1\\sub2'


def test_pathmanager_good_file():
    file_name = os.path.basename(__file__)
    dir_path = os.path.dirname(__file__)
    pm = paths.PathManager(__file__)
    assert pm.is_file
    assert not pm.is_dir
    assert pm.exists
    assert pm.extension() == '.py'
    assert pm.extension(False) == 'py'
    assert pm.basename() == file_name
    assert pm.basename(False) == file_name.split('.')[0]
    assert pm.construct('sub1', 'sub2') == os.path.join(dir_path, 'sub1', 'sub2', file_name)


def test_pathmanager_good_dir():
    dir_path = os.path.dirname(__file__)
    dir_name = os.path.basename(dir_path)
    pm = paths.PathManager(dir_path)
    assert not pm.is_file
    assert pm.is_dir
    assert pm.exists
    assert pm.extension() == ''
    assert pm.extension(False) == ''
    assert pm.basename() == dir_name
    assert pm.basename(False) == dir_name
    assert pm.construct('sub1', 'sub2') == os.path.join(dir_path, 'sub1', 'sub2')
