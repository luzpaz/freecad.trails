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
Base class for Tracker objects
"""

from DraftGui import todo

from .coin.coin_group import CoinGroup
from .publisher import Publisher
from .subscriber import Subscriber
from .event import Event
from ..support.view_state import ViewState
from ..support.mouse_state import MouseState
from .coin.coin_enums import CoinNodes as Nodes

#from ...containers import TrackerContainer

class Base(Publisher, Subscriber, Event):
    """
    Base class for Tracker objects
    """

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #'virtual' function declarations overriden by class inheritance
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    #Style
    def set_style(self, style=None, draw=None, color=None):
        """prototype"""; pass

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Class statics
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    #global view state singleton
    view_state = None
    mouse_state = None

    pathed_trackers = []

    """
    @staticmethod
    def search_node(node, parent=None):
       # "#""
       # Searches for a node, returning it's path.
       # Scenegraph root assumed if parent is None
        #"#""

        if not parent:
            parent = Base.view_state.sg_root

        _sa = coin.SoSearchAction()
        _sa.setNode(node)
        _sa.apply(parent)

        return _sa.getPath()

    @staticmethod
    def find_node(node, parent=None):
        #"#""
       # Find a node.
        #"#""

        _path = Base.search_node(node, parent)

        if _path:
            return _path.getTail()

        return None
    """
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Class Defiintion
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, name, parent=None):
        """
        Constructor
        """

        #name is three parts, delimited by periods ('doc.task.obj')
        #object name is always first
        self.names = name.split('.')[::-1]
        self.name = self.names[0]

        #pad array to ensure three elements
        if len(self.names) < 3:
            self.names += ['']*(3-len(self.names))

        if not Base.view_state:
            Base.view_state = ViewState()

        if not Base.mouse_state:
            Base.mouse_state = MouseState()

        #provide reference to scenegraph root for CoinGroup for default
        #node creation / destruction
        CoinGroup.scenegraph_root = Base.view_state.sg_root

        self.sg_root = self.view_state.sg_root

        self.callbacks = {}

        self.base = CoinGroup(
            is_separator=True, is_switched=True,
            name=self.name, parent=parent)

        self.base.path_node = None
        self.base.transform = self.base.add_node(Nodes.TRANSFORM, 'Transform')

        super().__init__()

    def insert_into_scenegraph(self):
        """
        Insert the base node into the scene graph and trigger notifications
        """

        _fn = lambda _x: Base.view_state.sg_root.insertChild(_x, 0)

        todo.delay(_fn, self.base.root)

    def finalize(self, node=None, parent=None):
        """
        Node destruction / cleanup
        """

        self.base.finalize()