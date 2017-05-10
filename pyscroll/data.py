"""
This file contains a few classes for accessing data

If you are developing your own map format, please use this
as a template.  Just fill in values that work for your game.
"""
import time
from itertools import product
from heapq import heappop, heappush

import pytmx

from pyscroll import rect_to_bb
from pyscroll.animation import AnimationFrame, AnimationToken

__all__ = ('PyscrollDataAdapter', 'TiledMapData')


class PyscrollDataAdapter(object):
    """ Use this as a template for data adapters
    
    Contains logic for handling animated tiles.  Animated tiles
    are a WIP feature, and while in theory will work with any data
    source, it is only tested using Tiled maps, loaded with pytmx.
    """

    # the following can be class/instance attributes
    # or properties.  they are listed here as class
    # instances, but use as properties is fine, too.

    tile_size = None             # (int, int): size of each tile in pixels
    map_size = None              # (int, int): size of map in tiles
    visible_tile_layers = None   # list of visible layer integers

    def __init__(self):
        self._last_time = None           # last time map animations were updated
        self._animation_queue = list()   # list of animation tokens
        self._animated_tile = dict()     # mapping of tile substitutions when animated
        self._tracked_tiles = set()      # track the tiles on screen with animations

    def process_animation_queue(self, tile_view):
        """ Given the time and the tile view, process tile changes and return them
        
        :param tile_view: rect representing tiles on the screen
        :type tile_view: pygame.Rect
        
        :rtype: list
        """

        # if there are no animations, just return
        if not self._animation_queue:
            return

        self._update_time()
        new_tiles = list()
        new_tiles_append = new_tiles.append
        tile_layers = tuple(self.visible_tile_layers)
        get_tile_image = self.get_tile_image

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:

            # get the next tile/frame which is ready to be changed
            token = heappop(self._animation_queue)
            next_frame = token.advance(self._last_time)
            heappush(self._animation_queue, token)

            # go through the animated tile map:
            #   * queue tiles that need to be changed
            #   * remove positions that do not collide with screen

            for position in self._tracked_tiles & token.positions:
                x, y, l = position

                # if this tile is on the buffer (checked by using the tile view)
                if tile_view.collidepoint(x, y):

                    # record the location of this tile, in case of a screen wipe, or sprite cover
                    self._animated_tile[position] = next_frame.image

                    # redraw the entire column of tiles
                    for layer in tile_layers:
                        if layer == l:

                            # queue the new animated tile
                            new_tiles_append((x, y, layer, next_frame.image))
                        else:

                            # queue the normal tile
                            image = get_tile_image(x, y, layer)
                            if image:
                                new_tiles_append((x, y, layer, image))

                # not on screen, but was previously.  clear it.
                else:
                    self._tracked_tiles.remove(position)

        return new_tiles

    def _update_time(self):
        """ Update the internal clock.
        
        This may change in future versions.
        
        :return: 
        """
        self._last_time = time.time() * 1000

    def reload_animations(self):
        """ Reload animation information
        
        This relies on the data source having references to tiles by
        an ID.  So far, this is not implemented outside of Tiled Maps.
        """
        raise NotImplementedError

    def get_tile_image(self, x, y, l):
        """ Get a tile image, respecting current animations

        :param x: x coordinate
        :param y: y coordinate
        :param l: layer

        :type x: int
        :type y: int
        :type l: int

        :rtype: pygame.Surface
        """
        # since the tile has been queried, assume it wants to be checked
        # for animations sometime in the future
        if self._animation_queue:
            self._tracked_tiles.add((x, y, l))

        try:
            # animated, so return the correct frame
            return self._animated_tile[(x, y, l)]

        except KeyError:

            # not animated, so return surface from data, if any
            return self._get_tile_image(x, y, l)

    def _get_tile_image(self, x, y, l):
        """ Return tile at the coordinates, or None is empty
       
        This is used to query the data source directly, without
        checking for animations or any other tile transformations.
        
        You must override this to support other data sources
        
        :param x: 
        :param y: 
        :param l: 
        
        :type x: int
        :type y: int
        :type l: int
        
        :return: 
        """
        raise NotImplementedError

    def convert_surfaces(self, parent, alpha=False):
        """ Convert all images in the data to match the parent

        :param alpha: if True, then do not discard alpha channel 
        :param parent: pygame.Surface
        
        :return: None
        """
        raise NotImplementedError

    def get_animations(self):
        """ Get tile animation data

        This method is subject to change in the future.

        Must yield tuples that in the following format:
          ( Position, Frames )

          Where Frames is:
          [ (Position, Duration), ... ]
    
          And Position is:
          ( x, y, l )

        :return: sequence
        """
        raise NotImplementedError

    def get_tile_images_by_rect(self, rect):
        """ Given a 2d area, return generator of tile images inside

        Given the coordinates, yield the following tuple for each tile:
          X, Y, Layer Number, pygame Surface

        This method also defines render order by re arranging the
        positions of each tile as it is yielded to the renderer.

        There is an optimization that you can make for your data:
        If you can provide access to tile information in a batch,
        then pyscroll can access data faster and render quicker.

        To implement this optimization, override this method.

        Not like python 'Range': should include the end index!

        :param rect: a rect-like object that defines tiles to draw
        :return: generator
        """
        x1, y1, x2, y2 = rect_to_bb(rect)
        for layer in self.visible_tile_layers:
            for y, x in product(range(y1, y2 + 1),
                                range(x1, x2 + 1)):
                tile = self.get_tile_image(x, y, layer)
                if tile:
                    yield x, y, layer, tile


class TiledMapData(PyscrollDataAdapter):
    """ For data loaded from pytmx

    Use of this class requires a recent version of pytmx.
    """

    def __init__(self, tmx):
        super(TiledMapData, self).__init__()
        self.tmx = tmx
        self.reload_animations()

    def get_animations(self):
        for gid, d in self.tmx.tile_properties.items():
            try:
                frames = d['frames']
            except KeyError:
                continue

            if frames:
                yield gid, frames

    def reload_animations(self):
        """ Reload animation information
        """
        self._update_time()
        self._animation_queue = list()

        for gid, frame_data in self.get_animations():
            frames = list()
            for frame_gid, frame_duration in frame_data:
                image = self.tmx.get_tile_image_by_gid(frame_gid)
                frames.append(AnimationFrame(image, frame_duration))

            positions = tuple(self.tmx.get_tile_locations_by_gid(gid))
            ani = AnimationToken(positions, frames, self._last_time)
            heappush(self._animation_queue, ani)

    def convert_surfaces(self, parent, alpha=False):
        """ Convert all images in the data to match the parent

        :param parent: pygame.Surface
        :param alpha: preserve alpha channel or not
        :return: None
        """
        images = list()
        for i in self.tmx.images:
            try:
                if alpha:
                    images.append(i.convert_alpha(parent))
                else:
                    images.append(i.convert(parent))
            except AttributeError:
                images.append(None)
        self.tmx.images = images

    @property
    def tile_size(self):
        """ This is the pixel size of tiles to be rendered
        
        :return: (int, int)
        """
        return self.tmx.tilewidth, self.tmx.tileheight

    @property
    def map_size(self):
        """ This is the size of the map in tiles
        
        :return: (int, int)
        """
        return self.tmx.width, self.tmx.height

    @property
    def visible_tile_layers(self):
        """ This must return layer numbers, not objects
        
        :return: [int, int, ...]
        """
        return (int(i) for i in self.tmx.visible_tile_layers)

    @property
    def visible_object_layers(self):
        """ This must return layer objects

        This is not required for custom data formats.

        :return: Sequence of pytmx object layers/groups
        """
        return (layer for layer in self.tmx.visible_layers
                if isinstance(layer, pytmx.TiledObjectGroup))

    def _get_tile_image(self, x, y, l):
        try:
            return self.tmx.get_tile_image(x, y, l)
        except ValueError:
            return None

    def get_tile_images_by_rect(self, rect):
        """ Speed up data access

        More efficient because data is accessed and cached locally
        """

        def rev(seq, start, stop):
            if start < 0:
                start = 0
            return enumerate(seq[start:stop + 1], start)

        x1, y1, x2, y2 = rect_to_bb(rect)
        images = self.tmx.images
        layers = self.tmx.layers
        tt_add = self._tracked_tiles.add
        at = self._animated_tile
        track = bool(self._animation_queue)

        for l in self.tmx.visible_tile_layers:
            for y, row in rev(layers[l].data, y1, y2):
                for x, gid in [i for i in rev(row, x1, x2) if i[1]]:
                    # since the tile has been queried, assume it wants to be checked
                    # for animations sometime in the future
                    if track:
                        tt_add((x, y, l))

                    try:
                        # animated, so return the correct frame
                        yield x, y, l, at[(x, y, l)]

                    except KeyError:

                        # not animated, so return surface from data, if any
                        yield x, y, l, images[gid]
