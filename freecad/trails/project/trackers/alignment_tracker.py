# -*- coding: utf-8 -*-
#**************************************************************************
#*                                                                     *
#* Copyright (c) 2019 Joel Graff <monograff76@gmail.com>               *
#*                                                                     *
#* This program is free software; you can redistribute it and/or modify*
#* it under the terms of the GNU Lesser General Public License (LGPL)  *
#* as published by the Free Software Foundation; either version 2 of   *
#* the License, or (at your option) any later version.                 *
#* for detail see the LICENCE text file.                               *
#*                                                                     *
#* This program is distributed in the hope that it will be useful,     *
#* but WITHOUT ANY WARRANTY; without even the implied warranty of      *
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
#* GNU Library General Public License for more details.                *
#*                                                                     *
#* You should have received a copy of the GNU Library General Public   *
#* License along with this program; if not, write to the Free Software *
#* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
#* USA                                                                 *
#*                                                                     *
#***********************************************************************
"""
Tracker for alignment drafting
"""

from pivy import coin

from FreeCAD import Vector

from ...geometry import support, arc
from ..support import utils
from .base_tracker import BaseTracker
from .coin_group import CoinGroup

class AlignmentTracker(BaseTracker):
    """
    Tracker class for alignment design
    """

    def __init__(self, doc, view, object_name, alignment):
        """
        Constructor
        """

        self.alignment = alignment
        self.pi_list = self.alignment.model.get_pi_coords()
        self.curves = self.alignment.get_curves()
        self.curve_idx = []
        self.conn_pi = []
        self.start_path = None
        self.drag_start = Vector()
        self.stations = [-1.0, -1.0]

        self.connection = CoinGroup('ALIGNMENT_TRACKER_CONNECTION', True)
        self.selection = CoinGroup('ALIGNMENT_TRACKER_SELECTION', True)

        self.viewport = \
            view.getViewer().getSoRenderManager().getViewportRegion()

        _names = [doc.Name, object_name, 'ALIGNMENT_TRACKER']
        super().__init__(names=_names, select=False, group=True)

    def build_selection_group(self, selected):
        """
        Build the selection group based on the passed selected PI's
        """

        _start_sta = -1.0

        for _curve in self.alignment.get_curves():

            if support.within_tolerance(_curve['PI'], selected[0], 0.1):
                _start_sta = _curve['InternalStation'][1]
                break

        #abort if starting point not found
        if _start_sta < 0.0:
            return

        _geo = self.alignment.model.discretize_geometry([_start_sta])

        self.selection.set_coordinates(_geo)

    def build_connection_group(self, selected):

        _pi_idx = -1

        for _i, _v in enumerate(self.pi_list):
            if support.within_tolerance(_v, _selected[0], 0.1):
                _pi_idx = _i
                break

        if _pi_idx == -1:
            return

        num_pi = len(self.pi_list)

        _pi_idx = []
        _curve_list = []
        #three nodes takes all, first or last selected takes all
        if num_pi == 3 or _pi_idx == 0:
            _pi_list = self.pi_list
            _curve_list = [self.curves[0]]
        elif _pi_idx == len(self.pi_list):
            _pi_list = self.pi_list[-3:]
            _curve_list = [self.curves[-1]]

        #otherwise four nodes, second from start or end, or multi-select
        elif num_pi == 4 or _pi_idx == 1:
            _pi_list = self.pi_list
            _curve_list = self.curves[0:2]
        elif _pi_idx == num_pi - 2:
            _pi_list = self.pi_list[-4:]
            _curve_list = self.curves[-2:]
        elif len(selected) > 1:
            _pi_list = self.pi_list[_pi_idx-2:_pi_idx+2]
            _curve_list = self.curves[_pi_idx-2:_pi_idx-1]

        #otherwise five nodes with index two or more from either end:
        else:
            _pi_list = self.pi_list[_pi_idx-2:_pi_idx+3]
            _curve_list = self.curves[_pi_idx-2:pi_idx]

    def build_connection_group_dep(self, selected):
        """
        Build the connection group based on the passed selected PI's
        """

        #when dragging, if only one node is selected, one PI is transformed
        #and three cruves are re-calculated
        #if multiple nodes are selected, two curves are recalculated

        _count = len(selected)
        _start_pi = selected[0]

        #get the pi index for the selected pi
        for _i, _v in enumerate(self.pi_list):

            if support.within_tolerance(_v, _start_pi, 0.1):
                self.start_pi = _i
                break

        #abort if we can't find the curve under the first selected PI
        if self.start_pi == -1:
            return coin.SoGroup()

        #get a list of curves to be updated
        self.curves = [_curves[_i] \
            if 0 <= _i < len(_curves) else None \
                for _i in list(range(self.start_pi - 2, self.start_pi + 1))
        ]

        #only the first two curves apply in multi-select cases,
        #so just save the next PI as a fake curve
        if _count > 1:
            self.curves[2] = None

        _sta = [_v['InternalStation'] for _v in self.curves if _v]

        #build scenegraph nodes
        _coords = self.model.discretize_geometry([_sta[0][0], _sta[-1][1]])

        self.conn_group.set_coordinates(_coords)

        return self.conn_group.group


    def get_transformed_coordinates(self, path, vecs):
        """
        Return the transformed coordinates of the selected nodes based
        on the transformations applied by the drag tracker
        """

        #get the matrix for the transformation
        _matrix = coin.SoGetMatrixAction(self.viewport)
        _matrix.apply(path)

        _xf = _matrix.getMatrix()

        #create the 4D vectors for the transformation
        _vecs = [coin.SbVec4f(tuple(_v) + (1.0,)) for _v in vecs]

        #multiply each coordinate by transformation matrix and return
        #a list of the transformed coordinates, omitting fourth value
        return [Vector(_xf.multVecMatrix(_v).getValue()[:3]) for _v in _vecs]

    def drag_callback(self, xform, path, pos):
        """
        Callback for drag operations
        """

        _new_curves = [
            self.curves[_i] if _i else None for _i in self.curve_idx
        ]

        #curve at index 1 will always be defined
        _new_pi = _new_curves[1]['PI'].add(xform)

        if _new_curves[0]:

            _new_curves[0] = {
                'PI': _new_curves[0]['PI'],
                'Radius': _new_curves[0]['Radius'],
                'BearingIn': _new_curves[0]['BearingIn'],
                'BearingOut': support.get_bearing(
                    _new_pi.sub(_new_curves[0]['PI']))
            }

        if _new_curves[1]:

            _b_in = None
            _b_out = None

            if _new_curves[0]:
                _b_in = _new_pi.sub(_new_curves[0]['PI'])

            if _new_curves[2]:
                _b_out = _new_curves[2]['PI'].sub(_new_pi)

            else:
                #get the PI following the selected curve for the bearing
                _xf_pi = self.pi_list[self.curve_idx[1] + 1]
                _xf_pi = self.get_transformed_coordinates(path, [_xf_pi])[0]

                _b_out = _xf_pi.sub(_new_pi)

            #this should never happen
            if not (_b_in or _b_out):
                print('Drag error - selected curve not found.')
                return

            _new_curves[1] = {
                'PI': _new_pi,
                'Radius': _new_curves[1]['Radius'],
                'BearingIn': support.get_bearing(_b_in),
                'BearingOut': support.get_bearing(_b_out)
            }

        #test to ensure it's not a fake curve for multi-select cases
        if _new_curves[2]:

            _new_curves[2] = {
                'PI': _new_curves[2]['PI'],
                'Radius': _new_curves[2]['Radius'],
                'BearingIn': support.get_bearing(
                    _new_curves[2]['PI'].sub(_new_pi)),
                'BearingOut': _new_curves[2]['BearingOut'],
            }

        _coords = []

        for _v in self.curves:

            if not _v:
                continue

            print('getting parameters for arc ', _v)
            _v[1] = arc.get_parameters(_v[1])

            _pts = arc.get_points(_v[1], _dtype=tuple)[0]
            _coords.extend(_pts)

        self.connection.set_coordinates(_coords)

    def begin_drag(self, selected):
        """
        Initialize for dragging operations, initializing selected portion
        of the alignment
        """

        #abort if only one PI is selected
        if len(selected) < 2:
            return

        self.build_selection_group(selected)
        self.build_connection_group(selected)

    def end_drag(self, path):
        """
        Cleanup after dragging operations
        """


        pass

    def finalize(self, node=None):
        """
        Override of the parent method
        """

        self.alignment = None

        if not node:
            node = self.node

        super().finalize(node)
