pyscroll
======

for Python 3 and Pygame 1.9

A simple, fast module for adding scrolling maps to your new or existing game.



Compatible with pytmx:
https://github.com/bitcraft/pytmx


What the heck is it?
====================

pyscroll is a generic module for making a fast scrolling image with PyGame.  It uses a lot of magic to get reasonable
framerates out of PyGame.  It only exists to draw a map.  It doesn't load images or data, so you can use your own custom
data structures, tile storage, ect.

The included class, BufferedRenderer, gives great framerates, supports layered rendering and can draw itself.  It uses
more memory than a typical map would, but gives much better performance.

Features
========

- Fast and lightweight
- Layered drawing
- Dirty screen updates


Usage
=====

Basically, you need an object that conforms to a simple protocol defined in pyscroll.TiledMapData.  And as luck would
have it, I've included an object that works with my Tiled TMX library.  https://github.com/bitcraft/pytmx


# Using a pyscroll map layer

pyscroll isn't a replacement for any PyGame objects.  You can it it along with your Sprites and SpriteGroups.

    # Load TMX data (optional)
    tmx_data = pytmx.load_pygame("desert.tmx")

    # Make data source for the map
    map_data = pyscroll.TiledMapData(tmx_data)

    # Make the scrolling layer
    size = (400, 400)
    map_layer = pyscroll.BufferedRenderer(map_data, size)

    # Center the layer on a pixel
    map_layer.center((200, 200))

    # Draw the layer
    rect = pygame.Rect(0,0,200,200)
    map_layer.draw(screen, rect)

    # Draw the layer in the background (optional)
    map_layer.update()

See the demo in tests for code.


Adapting Existing Games / Map Data
==================================

pyscroll can be used with existing map data, but you will have to create a class to interact with pyscroll
or adapt your data handler to have these functions / attributes:


    class MyData:
        def __init__(self, tmx):
            self.default_image = generate_default_image((tmx.tilewidth, tmx.tileheight))

        @property
        def tilewidth(self):
            """
            Return pixel width of map tiles
            """

        @property
        def tileheight(self):
            """
            Return pixel height of map tiles
            """

        @property
        def width(self):
            """
            Return number of tiles on X axis
            """

        @property
        def height(self):
            """
            Return number of tiles on Y axis
            """

        @property
        def visible_layers(self):
            """
            Return a list of layer numbers that are visible.
            If using a single layer map, just return [0]
            """

        def get_tile_image(self, position):
            """
            Return a surface for this position.
            Return self.default_image if there is not map data for the position.

            position is x, y, layer tuple
            """

        def convert(self, surface=None, depth=None, flags=0):
            """
            Optional.  Convert the surfaces to match the display.
            """

