import re
import os.path
import xml.etree.ElementTree as ET

NAVPOINT_PATH = 'data/'


def make_id(id):
    return re.sub(r'[-_]+', ' ', id.upper())


def points_from_svg(filename):
    """Load navigation points from the given SVG file."""
    path = os.path.join(NAVPOINT_PATH, filename + '.svg')
    tree = ET.parse(path)
    points = {}
    for e in tree.iter('{http://www.w3.org/2000/svg}use'):
        transform = e.get('transform')
        mo = re.match(r'translate\(([\d.]+),\s*([\d.]+)\)', transform)
        pos = tuple(round(float(g)) for g in mo.groups())
        id = make_id(e.get('id'))
        points[id] = pos
    assert points, "No nav points loaded from %s" % filename
    return points

