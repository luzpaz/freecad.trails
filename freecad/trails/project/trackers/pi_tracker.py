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
Customized wire tracker for PI alignments
"""

from pivy import coin

import FreeCADGui as Gui
import DraftTools

from DraftGui import todo

from .base_tracker import BaseTracker
from .node_tracker import NodeTracker
from .wire_tracker import WireTracker

from ..support.utils import Constants as C

class PiTracker(BaseTracker):
    """
    Tracker class which manages alignment PI  and tangnet
    picking and editing
    """

    def __init__(self, doc, object_name, node_name, points):
        """
        Constructor
        """

        #dict which tracks actions on nodes in the gui
        self.gui_nodes = {
            'drag': -1,
            'rollover': -1,
            'selected': [-1],
        }

        self.node_trackers = []
        self.wire_trackers = []
        self.callbacks = []

        self.button_states = {
            'BUTTON1': False,
            'BUTTON2': False,
            'BUTTON3': False
        }


        self.transform = coin.SoTransform()
        self.transform.translation.setValue([0.0, 0.0, 0.0])

        self.set_points(points=points, doc=doc, obj_name=object_name)

        child_nodes = [self.transform]

        super().__init__(names=[doc.Name, object_name, node_name],
                         children=child_nodes, select=False)

        for _tracker in self.node_trackers + self.wire_trackers:
            self.node.addChild(_tracker.node)

        self.color.rgb = (0.0, 0.0, 1.0)

        todo.delay(self._insertSwitch, self.node)

    def get_button_states(self, arg):
        """
        Set the mouse button state dict
        """

        state = arg.get('State')
        button = arg.get('Button')

        print(state, button)

        if not state or not button:
            return

        self.button_states[button] = state == 'DOWN'

    def setup_callbacks(self, view):
        """
        Setup event handling callbacks and return as a list
        """

        return [
            ('SoKeyboardEvent',
             view.addEventCallback('SoKeyboardEvent', self.key_action)
            ),
            ('SoLocation2Event',
             view.addEventCallback('SoLocation2Event', self.mouse_action)
            ),
            ('SoMouseButtonEvent',
             view.addEventCallback('SoMouseButtonEvent', self.button_action)
            )
        ]

    def key_action(self, arg):
        """
        Keypress actions
        """

        return

    def mouse_action(self, arg):
        """
        Mouse movement actions
        """

        _p = Gui.ActiveDocument.ActiveView.getCursorPos()
        info = Gui.ActiveDocument.ActiveView.getObjectInfo(_p)

        roll_node = self.gui_nodes['rollover']

        if not info:

            if roll_node > -1:

                self.node_trackers[roll_node].switch_node()
                roll_node = -1

        else:

            component = info['Component'].split('_')

            if component[0] == 'NODE':

                _idx = int(component[1])

                if _idx == self.gui_nodes['selected']:
                    return

                if _idx != roll_node:
                    self.gui_nodes['rollover'] = _idx

                self.node_trackers[self.gui_nodes['rollover']] \
                        .switch_node('rollover')

        DraftTools.redraw3DView()

    def button_action(self, arg):
        """
        Button actions
        """

        _p = Gui.ActiveDocument.ActiveView.getCursorPos()
        info = Gui.ActiveDocument.ActiveView.getObjectInfo(_p)

        sel_nodes = self.gui_nodes['selected']

        #a click means the current selection gets cleared
        if sel_nodes[0] > -1:
            for _node in sel_nodes:
                self.node_trackers[_node].switch_node('deselect')

            self.gui_nodes['selected'] = [-1]

        if not info:
            return

        #otherwise, split on underscore to get element type and index
        component = info['Component'].split('_')
        multi_select = arg['AltDown']

        if component[0] == 'NODE':

            _clicked = int(component[1])

            #if alt is held down (we're in multi-select mode)
            #select every node after the selected one as well
            self.gui_nodes['selected'] = [_clicked]

            if multi_select:

                idx_range = range(_clicked, len(self.node_trackers))
                self.gui_nodes['selected'] = [_x for _x in idx_range]

            nodes = [
                self.node_trackers[_i] for _i in self.gui_nodes['selected']
            ]

            for _node in nodes:
                _node.switch_node('select')

        DraftTools.redraw3DView()

    def update(self, points=None, placement=None):
        """
        Update
        """

        if points:
            self.update_points(points)

        if placement:
            self.update_placement(placement)

    def update_points(self, points):
        """
        Updates existing coordinates
        """

        _prev = None

        for _i, _pt in enumerate(points):

            for _node in self.node_trackers:
                _node.update(_pt)

            if _prev:
                self.wire_trackers[_i - 1].update([_prev, _pt])

            _prev = _pt

    def set_points(self, points, doc=None, obj_name=None):
        """
        Clears and rebuilds the wire and node trackers
        """

        self.finalize_trackers()

        prev_coord = None

        for _i, _pt in enumerate(points):

            #set z value on top
            _pt.z = C.Z_DEPTH[2]

            #build node trackers
            self.node_trackers.append(NodeTracker(
                names=[doc.Name, obj_name, 'NODE_' + str(_i)], point=_pt)
            )

            self.node_trackers[-1].update(_pt)

            if not prev_coord is None:

                continue
                points = [prev_coord, _pt]

                _wt = WireTracker(
                    names=[doc.Name, obj_name, 'WIRE_' + str(_i - 1)]
                )

                _wt.update_points(points)

                self.wire_trackers.append(_wt)

            prev_coord = _pt

    def update_placement(self, vector):
        """
        Updates the placement for the wire and the trackers
        """

        self.transform.translation.setValue(list(vector))

    def finalize_trackers(self, tracker_list=None):
        """
        Destroy existing trackers
        """

        if self.node_trackers:

            for _tracker in self.node_trackers:
                _tracker.finalize()

            self.node_trackers.clear()

        if self.wire_trackers:

            for _tracker in self.wire_trackers:
                _tracker.finalize()

            self.wire_trackers.clear()

    def finalize(self):
        """
        Override of the parent method
        """

        self.finalize_trackers()
        super().finalize(self.node)
