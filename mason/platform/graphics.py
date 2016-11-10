# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2016

This file is part of mason.

mason is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

mason is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with mason.  If not, see <http://www.gnu.org/licenses/>.
"""


class RendererAB(object):
    """ The Tiling logic is graphics library agnostic.

    To support a new graphics library, implement this class
    """
    def change_offset(self, x, y):
        """ Adjust the offset that the buffer is shown at

        :param x:
        :param y:
        :return:
        """
        raise NotImplementedError

    def change_view(self, dx, dy):
        """ Adjust the tiles that are shown

        :param dx:
        :param dy:
        :return:
        """
        raise NotImplementedError

    def new_buffer(self, size):
        """ Create new buffer for the map

        :param size:
        :return:
        """
        raise NotImplementedError

    def clear_buffer(self):
        """ Clear the buffer

        :return:
        """
        raise NotImplementedError

    def clear_screen(self):
        """ Clear the area of the screen where map is drawn

        :return:
        """
        raise NotImplementedError

    def create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        raise NotImplementedError

    def copy_buffer(self):
        """ Copy the buffer to the screen

        :return: None
        """
        raise NotImplementedError

    def flush_tile_queue(self, surface):
        """ Draw the queued tiles to the buffer and block until the tile queue is empty
        """
        raise NotImplementedError

    def draw_surfaces(self):
        """

        :return:
        """
        raise NotImplementedError

    def copy_sprite(self, destination, sprite, rect):
        """

        :param destination:
        :param sprite:
        :param rect:
        :return:
        """
        raise NotImplementedError
