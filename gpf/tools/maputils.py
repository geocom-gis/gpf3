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

"""
Module that simplifies working with layers in ArcMap.
"""
import typing as _tp

import gpf.common.textutils as _tu
import gpf.common.validate as _vld
import gpf.paths as _paths
from gpf.paths import split_gdbpath as _split
from gpf import arcpy as _arcpy


def get_mxd(path: str = None) -> '_arcpy.mapping.MapDocument':
    """
    Gets a MapDocument instance for the given MXD path.
    If *path* is ``None``, the current map document is retrieved. This will only work when this function is called
    by a script running within the context of ArcMap.

    :param path:        Path to the MXD or ``None``.
    :raises ValueError: If the MXD was not found or could not be read.

    .. seealso::        https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/mapdocument-class.htm
    """
    try:
        mxd_ref = _arcpy.mapping.MapDocument('CURRENT' if not path else path)
    except (AssertionError, OSError):
        raise ValueError('Map document at {} does not exist'.format(path) if path
                         else 'There is no current map document')
    return mxd_ref


def find_dataframe(mxd: '_arcpy.mapping.MapDocument', name: str = None, case_sensitive: bool = False):
    """
    Finds a data frame by its (case-insensitive) name in the given ArcMap document (MXD) and returns it.
    If no *name* is specified, the active data frame in the given Map Document is returned.
    If no data frame was found at all, ``None`` is returned. This can only happen, when looking for a specific *name*.

    :param mxd:                 A :class:`arcpy.mapping.MapDocument` instance.
    :param name:                The name of the data frame to search for.
    :param case_sensitive:      If ``True``, the data frame name needs to match exactly.
                                If ``False`` (default), the data frame character case is ignored.
    :rtype:                     arcpy._mapping.DataFrame

    .. seealso::                https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/dataframe-class.htm
    """
    df_ref = None
    if isinstance(name, str):
        name = _tu.to_str(name if case_sensitive else name.lower())
        for df in _arcpy.mapping.ListDataFrames(mxd):
            df_name = df.name if case_sensitive else df.name.lower()
            if df_name == name:
                df_ref = df
                break
    else:
        df_ref = mxd.activeDataFrame
    return df_ref


def _get_mxd_df(mxd: _tp.Union[str, '_arcpy.mapping.MapDocument'] = None,
                df=None, case_sensitive: bool = False) -> tuple:
    """ Private method to quickly retrieve references to an MXD and a (active) data frame. """
    mxd_ref = get_mxd(mxd) if not isinstance(mxd, _arcpy.mapping.MapDocument) else mxd
    df_ref = find_dataframe(mxd_ref, df, case_sensitive)
    return mxd_ref, df_ref


def find_layer(name: str, mxd: _tp.Union[str, '_arcpy.mapping.MapDocument'] = None,
               dataframe: str = None, case_sensitive: bool = False) -> '_arcpy.mapping.Layer':
    """
    Finds a **single** layer by its (case-insensitive) name in the specified ArcMap document (or current one).
    If the layer was not found, ``None`` is returned.

    :param name:            Name of the layer to find.
                            If the layer name exists multiple times in different group layers,
                            you can prefix the layer with the group layer name followed by a forward slash (/).
    :param mxd:             The path to the ArcMap Document (MXD) or a MapDocument instance in which to find the layer.
                            If no MXD is specified, the search will take place in the current MXD (if any).
    :param dataframe:       The name of the data frame in which to find the layer.
                            If no data frame is specified and/or there is only 1 data frame,
                            the search will take place in the active data frame.
    :param case_sensitive:  If ``True``, the layer name needs to match exactly.
                            If ``False`` (default), the layer character case is ignored.
                            Note that this setting also affects the *dataframe* argument, when specified.
    :raises ValueError:     If no layer name was specified, or if no map document was found.

    .. seealso::            https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/layer-class.htm
    """

    # Validation
    _vld.pass_if(_vld.has_value(name), ValueError, 'Layer name has not been specified')

    name = _tu.to_str(_paths.normalize(name, not case_sensitive))
    mxd_ref, df_ref = _get_mxd_df(mxd, dataframe, case_sensitive)

    # Find the layer by name
    for lyr in _arcpy.mapping.ListLayers(mxd_ref, data_frame=df_ref):
        lyr_name = lyr.name if case_sensitive else lyr.name.lower()
        if lyr_name == name or _paths.normalize(lyr.longName, not case_sensitive) == name:
            return lyr
    return None


def find_layers(wildcard: str = None, mxd: _tp.Union[str, '_arcpy.mapping.MapDocument'] = None,
                dataframe: str = None) -> _tp.List['_arcpy.mapping.Layer']:
    """
    Finds **all** layers that match a certain wild card expression in the specified ArcMap document (or current one).
    All matching layers are returned as a list of Layer instances. If no layers were found, an empty list is returned.

    :param wildcard:    Layer name search string (with wild card characters).
                        Unlike the :func:`find_layer` method, it is **not** possible to use a group layer prefix here.
                        Furthermore, the search string is case sensitive.
                        If this value is not specified, all layers in the map document will be returned.
    :param mxd:         The path to the ArcMap Document (MXD) or a MapDocument instance in which to find the layer(s).
                        If no MXD is specified, the search will take place in the current MXD (if any).
    :param dataframe:   The case-insensitive name of the data frame in which to find the layer(s).
                        If no data frame is specified and/or there is only 1 data frame,
                        the search will take place in the active data frame.
    :raises ValueError: If no map document was found.

    .. seealso::        https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/layer-class.htm
    """
    wildcard = None if not wildcard else _tu.to_str(wildcard)
    mxd_ref, df_ref = _get_mxd_df(mxd, dataframe)

    return _arcpy.mapping.ListLayers(mxd_ref, wildcard, df_ref) or []


def get_referenced_layers(dataset_path: str, mxd: _tp.Union[str, '_arcpy.mapping.MapDocument'] = None,
                          dataframe: str = None, strict: bool = True) -> _tp.List['_arcpy.mapping.Layer']:
    """
    Returns a list of all layers in which *dataset_path* is used as the data source.
    The search takes place in the specified *mxd* (or current one) in the given *dataframe* (or active one).
    All matching layers are returned as a list of Layer instances. If no layers were found, an empty list is returned.

    :param dataset_path:    The full path to the dataset (e.g. feature class, table) to find.
                            The path is case-insensitive, but if the layer data source is expected to have
                            database qualifiers, these should be included as well, unless *strict* is ``False``.
    :param mxd:             An optional path of the ArcMap document (MXD) to search through.
                            If no MXD is specified, the search will take place in the current MXD.
    :param dataframe:       The case-insensitive name of the data frame in which to find the layer(s).
                            If no data frame is specified and/or there is only 1 data frame,
                            the search will take place in the active data frame.
    :param strict:          If ``True`` (default) the case-insensitive data source path of the layer needs
                            to exactly match the *dataset_path*. For SDE connections, this could mean that the data
                            source will never be found. If *strict* is set to ``False``, only the feature class name
                            (and feature dataset name, if applicable) is matched.
    :raises ValueError:     If no map document was found.

    .. seealso::            https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/layer-class.htm
    """
    mxd_ref, df_ref = _get_mxd_df(mxd, dataframe)
    dataset_path = _paths.get_abs(dataset_path).lower()
    ds_parts = []

    layers = []
    for lyr in _arcpy.mapping.ListLayers(mxd_ref, data_frame=df_ref):
        lyr_path = lyr.dataSource.lower()
        if lyr_path == dataset_path:
            layers.append(lyr)
            continue
        if not strict:
            lyr_parts = _split(lyr_path)[1:]
            if not ds_parts:
                ds_parts = _split(dataset_path)[1:]
            if lyr_parts == ds_parts:
                layers.append(lyr)
    return layers


def get_layer_selection(layer: _tp.Union[str, '_arcpy.mapping.Layer'],
                        mxd: _tp.Union[str, '_arcpy.mapping.MapDocument'] = None,
                        dataframe: str = None, case_sensitive: bool = False) -> set:
    """
    Returns a ``set`` of selected Object ID's for the given layer name or Layer instance.
    Note that this might return an empty set if no features or rows are selected for the given layer.
    This behaviour is different from the standard call to :func:`getSelectionSet` on an ArcMap ``Layer`` object:
    if no selection is present, arcpy returns ``None`` instead.

    :param layer:           Layer instance or the name of the layer for which to get the selected Object ID's.
                            If the layer name exists multiple times in different group layers,
                            you can prefix the layer with the group layer name followed by a forward slash (/).
                            If a Layer instance is used as input, all other arguments are ignored and
                            the selection set is returned immediately.
    :param mxd:             The path to the ArcMap Document (MXD) or a MapDocument instance in which to find the layer.
                            If no MXD is specified, the search will take place in the current MXD (if any).
    :param dataframe:       The name of the data frame in which to find the layer.
                            If no data frame is specified and/or there is only 1 data frame,
                            the search will take place in the active data frame.
    :param case_sensitive:  If ``True``, the layer name needs to match exactly.
                            If ``False`` (default), the layer character case is ignored.
                            Note that this setting also affects the *dataframe* argument, when specified.

    .. seealso::            https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/layer-class.htm
    """
    if isinstance(layer, _arcpy.mapping.Layer):
        return layer.getSelectionSet() or set()
    lyr = find_layer(layer, mxd, dataframe, case_sensitive)
    if not lyr:
        return set()
    return lyr.getSelectionSet() or set()
