pyscroll
========

for Python 2.7 & 3.3 and Pygame 1.9

A simple, fast module for adding scrolling maps to your new or existing game.


Introduction
============

pyscroll is a generic module for making a fast scrolling image with PyGame.  It uses a lot of magic to get reasonable
framerates out of PyGame.  It only exists to draw a map.  It doesn't load images or data, so you can use your own custom
data structures, tile storage, ect.

The included class, BufferedRenderer, gives great framerates, supports layered rendering and can draw itself.  It uses
more memory than a typical map would, but gives much better performance.

pyscroll is compatible with pytmx (https://github.com/bitcraft/pytmx), so you can use your Tiled maps.  It also has out-of-the-box support for PyGame Sprites.

Features
========

- Fast and small footprint
- Layered drawing
- Dirty screen updates
- Pygame Group included


Tutorial
========

Open quest.py in the tutorial folder for a gentle introduction to pyscroll and the PyscrollGroup for PyGame.  There are plenty of comments to get you started.

pyscroll and pytmx can load your maps from Tiled and use you PyGame Sprites.

    # Load TMX data (optional)
    tmx_data = pytmx.load_pygame("desert.tmx")

    # Make data source for the map
    map_data = pyscroll.TiledMapData(tmx_data)

    # Make the scrolling layer
    # this size must match your screen size
    size = (400, 400)            
    map_layer = pyscroll.BufferedRenderer(map_data, size)

    # make the PyGame SpriteGroup with a scrolling map
    group = PyscrollGroup(map_layer=map_layer)

    # Add sprites to the group
    group.add(srite)
    
    # Center the layer and sprites on a sprite
    group.center(sprite.rect.center)

    # Draw the layer
    group.draw(screen)


Look in tutorial/code/quest.py for full source code and a simple demo.


Adapting Existing Games / Map Data
==================================

pyscroll can be used with existing map data, but you will have to create a class to interact with pyscroll
or adapt your data handler to have these functions / attributes:


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

