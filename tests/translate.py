"""
For testing the translate methods

incomplete
"""

for spr in self.sprites():
    r = self._map_layer.translate_rect(spr.rect)
    pygame.draw.rect(surface, (20, 20, 20), r, 1)

for spr in self.sprites():
    r = self._map_layer.translate_point(spr.rect.topleft)
    pygame.draw.circle(surface, (20, 20, 20), r, 3)

spr_list = list()
for spr in self.sprites():
    spr_list.append(spr.rect)

for r in self._map_layer.translate_rects(spr_list):
    pygame.draw.rect(surface, (200, 10, 10), r, 1)

for p in self._map_layer.translate_points([i.topleft for i in spr_list]):
    pygame.draw.circle(surface, (200, 10, 10), p, 3)
