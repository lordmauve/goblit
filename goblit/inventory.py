from .loaders import load_image


class FloorItem(object):
    def __init__(self, item, pos):
        self.item = item
        self.pos = pos

    @property
    def z(self):
        """Z-coordinate is always behind other items"""
        return 0

    def click_action(self):
        return 'Pick up %s' % self.item.name

    @property
    def bounds(self):
        r = self.item.image.get_rect()
        r.topleft = self.pos
        return r

    def draw(self, screen):
        im = self.item.image
        screen.blit(im, self.pos)


class Item:
    """Inventory item.

    Can also be spawned into the scene.

    """

    # Registry of all items
    items = {}

    def __init__(self, name, image_name=None):
        self.name = name.upper()
        self.image_name = image_name or name.lower().replace(' ', '-')
        self.items[self.name] = self
        self._im = self._icon = None

    @property
    def image(self):
        if self._im:
            return self._im
        self._im = load_image(self.image_name)
        return self._im

    @property
    def icon(self):
        if self._icon:
            return self._icon
        self._icon = load_image(self.image_name + '-icon')
        return self._icon


sock = Item('sock')
