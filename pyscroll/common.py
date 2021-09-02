from contextlib import contextmanager


@contextmanager
def surface_clipping_context(surface, clip):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


def rect_difference(a, b):
    """ Compute difference of two rects.  Returns up to 4.

    :type a: Rect
    :type b: Rect
    :rtype: list
    """
    raise NotImplementedError


def rect_to_bb(rect):
    x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1