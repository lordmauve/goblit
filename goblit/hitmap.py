from pygame import Rect
import os.path
import xml.etree.ElementTree as ET

from .navpoints import make_id

HITMAP_PATH = 'data/'


class HitMap:
    @classmethod
    def from_svg(cls, filename):
        path = os.path.join(HITMAP_PATH, filename + '.svg')
        tree = ET.parse(path)
        regions = {}
        for e in tree.iter('{http://www.w3.org/2000/svg}rect'): #findall('.//{http://www.w3.org/2000/svg}rect'):
            w = int(e.get('width'))
            h = int(e.get('height'))
            x = round(float(e.get('x')))
            y = round(float(e.get('y')))
            id = make_id(e.get('id'))
            regions[id] = Rect(x, y, w, h)
        assert regions, "No regions loaded from %s" % filename
        return cls(regions)

    def __init__(self, regions):
        self.regions = regions

    def region_for_point(self, pos):
        for id, rect in self.regions.items():
            if rect.collidepoint(pos):
                return id

    def get_point(self, name):
        r = self.regions.get(name)
        if r:
            return r.center
        return None
