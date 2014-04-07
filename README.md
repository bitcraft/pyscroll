pyscroll
===============================================================================

### A module for scrolling maps with PyGame.
##### For python 3.3+
##### *Use the python2 branch for Python 2.7 support*

bitcraft (leif dot theden at gmail.com)

*Released under the LGPL v3*


Compatible with pytmx:    
https://github.com/bitcraft/pytmx


What the heck is it?
===============================================================================

pyscroll is a generic module for making a fast scrolling image with PyGame.  It uses a lot of magic to get reasonable
framerates out of PyGame.  It only exists to draw a map.  It doesn't load images or data, so you can use your own custom
data structures, tile storage, ect.

The included class, BufferedRenderer, supports layered rendering and can draw itself.  It uses more memory than a typical map would, but gives good performance.

Features
===============================================================================

- Fast and lightweight
- Layered drawing
- Dirty screen updates


Using pyscroll with a new project
===============================================================================

pyscroll isn't a replacement for any PyGame objects.  You can it it along with
your Sprites and SpriteGroups.

    # Load TMX data
    tmx_data = pytmx.load_pygame("desert.tmx")

    # Make data source for the map
    map_data = pyscroll.TiledMapData(tmx_data)

    # Make the scrolling layer
    size = (400, 400)
    map_layer = pyscroll.BufferedRenderer(map_data, size)

    # Center the layer on a pixel for scroll that map
    map_layer.center((200, 200))

    # Draw the layer
    rect = pygame.Rect(0,0,200,200)
    map_layer.draw(screen, rect)

    # Draw the layer in the background (optional)
    map_layer.update()

See the demo in tests for code.


Adapting Existing Games / Map Data
===============================================================================

pyscroll can be used with existing map data.  You will have to create a class
to interact with pyscroll or adapt your data handler to have that data
interface.  If you don't have an existing map object, I've included a class
that works with my Tiled TMX library.   

https://github.com/bitcraft/pytmx


Heres a basic Data class that you can extend to use PyScroll with your existing
project:

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

