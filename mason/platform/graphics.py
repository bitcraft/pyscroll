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
    def _change_offset(self, d, y):
        raise NotImplementedError

    def _change_view(self, dx, dy):
        raise NotImplementedError

    def _new_buffer(self, size):
        raise NotImplementedError

    def _clear_buffer(self, target, color):
        raise NotImplementedError

    def _clear_screen(self):
        """ Clear the area of the screen where map is drawn

        :return:
        """
        raise NotImplementedError

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        raise NotImplementedError

    def _copy_buffer(self):
        """ Copy the buffer to the screen

        :return: None
        """
        raise NotImplementedError

    def _flush_tile_queue(self, surface):
        """ Draw the queued tiles to the buffer and block until the tile queue is empty
        """
        raise NotImplementedError

    def _draw_map(self, surface, rect, surfaces):
        """ Render the map and optional surfaces to destination surface

        :param surface: pygame surface to draw to
        :param rect: area to draw to
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """
        raise NotImplementedError
