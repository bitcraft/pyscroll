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
data structures, or choose from a few that exist already.


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
