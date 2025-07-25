"""
This file contains a few classes for accessing data

If you are developing your own map format, please use this
as a template.  Just fill in values that work for your game.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from heapq import heappop, heappush
from itertools import product
from typing import Any, Optional

import pygame
from pygame import Rect, Surface

try:
    # optional pytmx support
    import pytmx
except ImportError:
    pass

from .animation import AnimationFrame, AnimationToken
from .common import RectLike, Vector2DInt, rect_to_bb

__all__ = (
    "PyscrollDataAdapter",
    "TiledMapData",
    "MapAggregator",
)


class PyscrollDataAdapter:
    """
    Use this as a template for data adapters

    Contains logic for handling animated tiles.  Animated tiles
    are a WIP feature, and while in theory will work with any data
    source, it is only tested using Tiled maps, loaded with pytmx.

    """

    # the following can be class/instance attributes
    # or properties.  they are listed here as class
    # instances, but use as properties is fine, too.

    # (int, int): size of each tile in pixels
    tile_size: Vector2DInt = (0, 0)
    # (int, int): size of map in tiles
    map_size: Vector2DInt = (0, 0)
    # list of visible layer integers
    visible_tile_layers: list[int] = []

    def __init__(self) -> None:
        # last time map animations were updated
        self._last_time: float = 0.0
        # list of animation tokens
        self._animation_queue: list[AnimationToken] = []
        # mapping of tile substitutions when animated
        self._animated_tile: dict[tuple[int, int, int], Surface] = {}
        # track the tiles on screen with animations
        self._tracked_tiles = set()

    def reload_data(self) -> None:
        raise NotImplementedError

    def process_animation_queue(
        self,
        tile_view: Rect,
    ) -> list[tuple[int, int, int, Surface]]:
        """
        Given the time and the tile view, process tile changes and return them

        Args:
            tile_view: Rect representing tiles on the screen

        """
        new_tiles = list()

        # verify that there are tile substitutions ready
        self._update_time()
        try:
            if self._animation_queue[0].next > self._last_time:
                return new_tiles

        # raised with the animation queue is empty (no animations at all)
        except IndexError:
            return new_tiles

        new_tiles_append = new_tiles.append
        tile_layers = tuple(self.visible_tile_layers)
        get_tile_image = self.get_tile_image

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:

            # get the next tile/frame which is ready to be changed
            token = heappop(self._animation_queue)
            next_frame = token.advance(self._last_time)
            heappush(self._animation_queue, token)

            # following line for when all gid positions are known
            # for position in self._tracked_tiles & token.positions:

            for position in token.positions.copy():
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
                    token.positions.remove(position)

        return new_tiles

    def _update_time(self) -> None:
        """
        Update the internal clock.

        This may change in future versions.

        """
        self._last_time = time.time() * 1000

    def prepare_tiles(self, tiles: RectLike) -> None:
        """
        Somewhat experimental: The renderer will advise data layer of its view

        For some data providers, it would be useful to know what tiles will be drawn
        before they are ready to draw.  This exposes the tile view to the data.

        * A draw will happen immediately after this returns.
        * Do not hold on to this reference or change it.

        Args:
            tiles: Reference to the tile view

        """
        pass

    def reload_animations(self) -> None:
        """
        Reload animation information.

        PyscrollDataAdapter.get_animations must be implemented

        """
        self._update_time()
        self._tracked_gids: set[int] = set()
        self._animation_map: dict[int, AnimationToken] = {}

        for gid, frame_data in self.get_animations():
            self._tracked_gids.add(gid)

            frames: list[AnimationFrame] = []
            for frame_gid, frame_duration in frame_data:
                image = self._get_tile_image_by_id(frame_gid)
                frames.append(AnimationFrame(image, frame_duration))

            # the following line is slow when loading maps, but avoids overhead when rendering
            # positions = set(self.tmx.get_tile_locations_by_gid(gid))

            # ideally, positions would be populated with all the known
            # locations of an animation, but searching for their locations
            # is slow. so it will be updated as the map is drawn.

            positions: set[tuple[int, int, int]] = set()
            ani = AnimationToken(positions, frames, self._last_time)
            self._animation_map[gid] = ani
            heappush(self._animation_queue, ani)

    def get_tile_image(self, x: int, y: int, l: int) -> Surface:
        """
        Get a tile image, respecting current animations.

        Args:
            x: x coordinate
            y: y coordinate
            l: layer

        """
        # disabled for now, re-enable when support for generic maps is restored
        # # since the tile has been queried, assume it wants to be checked
        # # for animations sometime in the future
        # if self._animation_queue:
        #     self._tracked_tiles.add((x, y, l))

        try:
            # animated, so return the correct frame
            return self._animated_tile[(x, y, l)]

        except KeyError:

            # not animated, so return surface from data, if any
            return self._get_tile_image(x, y, l)

    def _get_tile_image(self, x: int, y: int, l: int) -> Surface:
        """
        Return tile at the coordinates, or None is empty.

        This is used to query the data source directly, without
        checking for animations or any other tile transformations.

        You must override this to support other data sources

        Args:
            x: x coordinate
            y: y coordinate
            l: layer

        """
        raise NotImplementedError

    def _get_tile_image_by_id(self, id: int) -> Any:
        """
        Return Image by a custom ID.

        Used for animations.  Not required for static maps.

        Args:
            id:

        """
        raise NotImplementedError

    def get_animations(self) -> None:
        """
        Get tile animation data.

        This method is subject to change in the future.

        Must yield tuples that in the following format:
          ( ID, Frames )

          Where Frames is:
          [ (ID, Duration), ... ]

          [tuple[int, tuple[int, float]]]
          [tuple[gid, tuple[frame_gid, frame_duration]]]

          And ID is a reference to a tile image.
          This will be something accessible using _get_tile_image_by_id

          Duration should be in milliseconds

        """
        raise NotImplementedError

    def get_tile_images_by_rect(self, rect: RectLike):
        """
        Given a 2d area, return generator of tile images inside.

        Given the coordinates, yield the following tuple for each tile:
          X, Y, Layer Number, pygame Surface

        This method also defines render order by re arranging the
        positions of each tile as it is yielded to the renderer.

        There is an optimization that you can make for your data:
        If you can provide access to tile information in a batch,
        then pyscroll can access data faster and render quicker.

        To implement this optimization, override this method.

        Not like python 'Range': should include the end index!

        Args:
            rect: Rect-like object that defines tiles to draw

        """
        x1, y1, x2, y2 = rect_to_bb(rect)
        for layer in self.visible_tile_layers:
            for y, x in product(range(y1, y2 + 1), range(x1, x2 + 1)):
                tile = self.get_tile_image(x, y, layer)
                if tile:
                    yield x, y, layer, tile


class TiledMapData(PyscrollDataAdapter):
    """
    For data loaded from pytmx.

    """

    def __init__(self, tmx: pytmx.TiledMap) -> None:
        super(TiledMapData, self).__init__()
        self.tmx = tmx
        self.reload_animations()

    def reload_data(self) -> None:
        self.tmx = pytmx.load_pygame(self.tmx.filename)

    def get_animations(self):
        for gid, d in self.tmx.tile_properties.items():
            try:
                frames = d["frames"]
            except KeyError:
                continue

            if frames:
                yield gid, frames

    def convert_surfaces(self, parent: Surface, alpha: bool = False) -> None:
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
    def tile_size(self) -> Vector2DInt:
        return self.tmx.tilewidth, self.tmx.tileheight

    @property
    def map_size(self) -> Vector2DInt:
        return self.tmx.width, self.tmx.height

    @property
    def visible_tile_layers(self):
        return self.tmx.visible_tile_layers

    @property
    def visible_object_layers(self) -> Iterable[pytmx.TiledObjectGroup]:
        return (
            layer
            for layer in self.tmx.visible_layers
            if isinstance(layer, pytmx.TiledObjectGroup)
        )

    def _get_tile_image(self, x: int, y: int, l: int):
        try:
            return self.tmx.get_tile_image(x, y, l)
        except ValueError:
            return None

    def _get_tile_image_by_id(self, id: int) -> Surface:
        return self.tmx.images[id]

    def get_tile_images_by_rect(self, rect: RectLike):
        def rev(seq: list[int], start: int, stop: int) -> enumerate[int]:
            if start < 0:
                start = 0
            return enumerate(seq[start : stop + 1], start)

        x1, y1, x2, y2 = rect_to_bb(rect)
        images = self.tmx.images
        layers = self.tmx.layers
        at = self._animated_tile
        tracked_gids = self._tracked_gids
        anim_map = self._animation_map
        track = bool(self._animation_queue)

        for l in self.tmx.visible_tile_layers:
            for y, row in rev(layers[l].data, y1, y2):
                for x, gid in [i for i in rev(row, x1, x2) if i[1]]:
                    # since the tile has been queried, assume it wants
                    # to be checked for animations sometime in the future
                    if track and gid in tracked_gids:
                        anim_map[gid].positions.add((x, y, l))
                    try:
                        # animated, so return the correct frame
                        tile = at[(x, y, l)]
                    except KeyError:
                        # not animated, so return surface from data, if any
                        tile = images[gid]
                    if tile:
                        yield x, y, l, tile


class MapAggregator(PyscrollDataAdapter):
    """
    Combine multiple data sources with an offset

    Currently this is just in a test phase.

    Has the following limitations:
    - Tile sizes must be the same for all maps
    - No tile animations
    - Sprites cannot be under layers
    - Cannot remove maps once added

    """

    def __init__(self, tile_size: Vector2DInt) -> None:
        super().__init__()
        self.tile_size = tile_size
        self.map_size = 0, 0
        self.maps: list[tuple[PyscrollDataAdapter, Rect, int]] = []
        self._min_x = 0
        self._min_y = 0

    def _get_tile_image(self, x: int, y: int, l: int) -> Optional[Surface]:
        """
        Required for sprite collation - not implemented.
        """
        pass

    def _get_tile_image_by_id(self, id: int) -> None:
        """
        Required for sprite collation - not implemented.
        """
        pass

    def add_map(
        self, data: PyscrollDataAdapter, offset: Vector2DInt, layer: int = 0
    ) -> None:
        """
        Add map data and position it with an offset.

        Args:
            data: Data Adapter, such as TiledMapData
            offset: Where the upper-left corner is, in tiles
            layer: The layer of the map
        """
        if data.tile_size != self.tile_size:
            raise ValueError("Tile sizes must be the same for all maps.")

        rect = pygame.Rect(offset, data.map_size)
        self._min_x = min(self._min_x, offset[0])
        self._min_y = min(self._min_y, offset[1])

        # the renderer cannot deal with negative tile coordinates,
        # so we must move all the offsets if there is a negative so
        # that all the tile coordinates are >= (0, 0)
        self.maps.append((data, rect, layer))
        self._adjust_map_positions(offset)
        self._update_map_size()

    def remove_map(self, data: PyscrollDataAdapter) -> None:
        """
        Removes a map from the aggregator.

        Args:
            data: The data adapter of the map to remove.
        """
        if data not in [m[0] for m in self.maps]:
            raise ValueError("Map is not in the aggregator")
        self.maps = [m for m in self.maps if m[0] != data]
        self._update_map_size()

    def _adjust_map_positions(self, offset: Vector2DInt) -> None:
        """Adjusts map positions based on negative offsets."""
        ox = self._min_x - offset[0]
        oy = self._min_y - offset[1]
        if ox > 0 or oy > 0:
            for _, rect, _ in self.maps:
                rect.move_ip((ox, oy))
        else:
            for _, rect, _ in self.maps:
                rect.move_ip(-self._min_x, -self._min_y)

    def _update_map_size(self) -> None:
        """Updates the overall map size."""
        mx = 0
        my = 0
        for _, rect, _ in self.maps:
            mx = max(mx, rect.right)
            my = max(my, rect.bottom)
        self.map_size = mx, my

    def get_animations(self) -> None:
        """
        Get animations - not implemented
        """
        pass

    def reload_data(self) -> None:
        """
        Reload the tiles - not implemented
        """
        pass

    @property
    def visible_tile_layers(self) -> list[int]:
        """
        Returns a sorted list of all visible tile layers from all added maps.
        """
        layers = set()
        for data, rect, z in self.maps:
            layers.update(list(data.visible_tile_layers))
        return sorted(layers)

    def get_tile_images_by_rect(
        self, view: pygame.Rect
    ) -> Iterable[tuple[int, int, int, Surface]]:
        """
        Yields tile images within the given view rectangle from all added maps.

        Args:
            view: Rect-like object defining the tile view.
        """
        view = pygame.Rect(view)
        for data, rect, z in self.maps:
            ox, oy = rect.topleft
            clipped = rect.clip(view).move(-ox, -oy)
            if clipped.width > 0 and clipped.height > 0:
                for x, y, l, image in data.get_tile_images_by_rect(clipped):
                    yield x + ox, y + oy, l, image

    def __repr__(self) -> str:
        return f"MapAggregator(tile_size={self.tile_size}, maps={self.maps})"

    def __len__(self) -> int:
        return len(self.maps)
