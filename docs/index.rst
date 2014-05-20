.. pyscroll documentation master file, created by
   sphinx-quickstart on Mon May 19 21:53:31 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pyscroll
========

for Python 2.7 & 3.3 and Pygame 1.9

A simple, fast module for adding scrolling maps to your new or existing game.


Introduction
============

pyscroll is a generic module for making a fast scrolling image with PyGame.  It
uses a lot of magic to get reasonable framerates out of PyGame.  It only exists
to draw a map.  It doesn't load images or data, so you can use your own custom
data structures, tile storage, ect.

The included class, BufferedRenderer, gives great framerates, supports layered
rendering and can draw itself.  It uses more memory than a typical map would,
but gives much better performance.

pyscroll is compatible with pytmx (https://github.com/bitcraft/pytmx), so you
can use your Tiled maps.  It also has out-of-the-box support for PyGame Sprites.


Features
========

- Fast and small footprint
- Layered drawing for tiles
- Drawing and scrolling shapes
- Dirty screen updates
- Pygame Group included


Shape Drawing
=============

pyscroll has a new experimental feature for drawing shapes to the map and
scrolling them as part of the map.  This can be useful for game that need to
draw arbitrary shaped objects.

The feature requires pytmx, and that the map files be created in the Tiled Map
Editor.  The advantage of of using pyscroll for shape drawing is that pyscroll
can draw the shapes much more efficiently that simply drawing the shapes each
frame.

This feature is experimental at best.  Your comments and support is appreciated!

* Currently, shapes will not draw over sprites.


New Game Tutorial
=================

This is a quick guide on building a new game with pyscroll and pygame.  It uses
the PyscrollGroup for efficient rendering.  You are free to use any other pygame
techniques and functions.

Open quest.py in the tutorial folder for a gentle introduction to pyscroll and
the PyscrollGroup for PyGame.  There are plenty of comments to get you started.

The Quest demo shows how you can use a pyscroll group for drawing, how to load
maps with PyTMX, and how pyscroll can quickly render layers.  Moving under some
tiles will cause the Hero to be covered.

It will also render a Shape on the map with experimental shape drawing.


Example Use with PyTMX
======================

pyscroll and pytmx can load your maps from Tiled and use you PyGame Sprites.

.. code-block:: python

    # Load TMX data
    tmx_data = pytmx.load_pygame("desert.tmx")

    # Make data source for the map
    map_data = pyscroll.TiledMapData(tmx_data)

    # Make the scrolling layer
    screen_size = (400, 400)
    map_layer = pyscroll.BufferedRenderer(map_data, screen_size)

    # make the PyGame SpriteGroup with a scrolling map
    group = pyscroll.PyscrollGroup(map_layer=map_layer)

    # Add sprites to the group
    group.add(srite)

    # Center the layer and sprites on a sprite
    group.center(sprite.rect.center)

    # Draw the layer
    group.draw(screen)


Adapting Existing Games / Map Data
==================================

pyscroll can be used with existing map data, but you will have to create a
class to interact with pyscroll or adapt your data handler to have these
functions / attributes:


.. code-block:: python

    class MyData:

        @property
        def tilewidth(self):
            """ Return pixel width of map tiles
            """

        @property
        def tileheight(self):
            """ Return pixel height of map tiles
            """

        @property
        def width(self):
            """ Return number of tiles on X axis
            """

        @property
        def height(self):
            """ Return number of tiles on Y axis
            """

        @property
        def visible_layers(self):
            """ Return a list or iterator of layer numbers that are visible.
            If using a single layer map, just return [0]
            """

        def get_tile_image(self, position):
            """ Return a surface for this position.
            Return self.default_image if there is not map data for the position.
            position is x, y, layer tuple
            """

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

