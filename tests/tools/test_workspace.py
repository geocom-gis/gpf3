# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

import pytest

import geocom.tools.workspace as workspace


def test_getworkspace():
    assert workspace.get_workspace(r'C:/temp/test.gdb/feature_dataset/feature_class') == \
           workspace.WorkspaceManager('C:\\temp\\test.gdb\\feature_dataset')
    assert workspace.get_workspace(
            r'C:/temp/test.gdb/feature_dataset/feature_class', True) == workspace.WorkspaceManager('C:\\temp\\test.gdb')


def test_isgdbpath():
    assert workspace.split_gdbpath(r'C:/folder/test.gdb/q.fds/q.fc') == ('C:\\folder\\test.gdb', 'fds', 'fc')
    assert workspace.split_gdbpath(r'C:/test.sde/q.fds/q.fc', False) == ('C:\\test.sde', 'q.fds', 'q.fc')
    with pytest.raises(ValueError):
        workspace.split_gdbpath(r'C:/test.gdb/folder/test2.gdb/subfolder')
        workspace.split_gdbpath(r'C:/test.gdb/a/b/c')


def test_wsmanager_gdb():
    wm = workspace.WorkspaceManager('test.gdb', qualifier='TEST', base=r'C:/temp', separator='|')
    assert wm.root == workspace.WorkspaceManager(r'C:/temp/test.gdb')
    assert wm.qualifier == ''
    assert wm.separator == ''
    assert wm.construct('ele', 'ele_kabel') == 'C:\\temp\\test.gdb\\ele\\ele_kabel'
    wm = workspace.WorkspaceManager(r'C:/temp/test.gdb')
    assert not wm.exists
    assert wm.root == workspace.WorkspaceManager(r'C:/temp/test.gdb')
    assert wm.get_parent(str(wm)) == 'C:\\temp\\test.gdb'
    assert wm.get_parent(str(wm), True) == 'C:\\temp'
    assert wm.get_root(str(wm)) == 'C:\\temp\\test.gdb'
    assert wm.is_gdb is True
    assert wm.qualifier == ''
    assert wm.separator == ''
    assert wm.qualify('test', 'my_qualifier') == 'test'
    with pytest.raises(ValueError):
        wm.qualify('')
    assert wm.construct('ele', 'ele_kabel') == 'C:\\temp\\test.gdb\\ele\\ele_kabel'
    with pytest.raises(IndexError):
        wm.construct('p1', 'p2', 'p3')
    assert workspace.WorkspaceManager.get_root(r'C:/temp/test.shp') == 'C:\\temp'
    assert workspace.WorkspaceManager.get_parent(r'C:/temp/test.shp') == 'C:\\temp'
    assert wm.get_root('C:\\temp\\test.gdb\\ele\\ele_kabel') == 'C:\\temp\\test.gdb'
