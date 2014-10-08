from pygame import Rect
from .loaders import load_image
from .actions import Action


class FloorItem(object):
    def __init__(self, scene, item, pos):
        self.scene = scene
        self.item = item
        self.pos = pos

    @property
    def name(self):
        return self.item.name

    @property
    def z(self):
        """Z-coordinate is always behind other items"""
        return 0

    def click_actions(self):
        """Get actions for the given object.

        Only one will actually be used; therefore ensure that operations that
        do things go above purely aesthetic ones.

        """
        return [
            Action('Pick up %s' % self.name, self.click),
            Action('Look at %s' % self.name)
        ]

    def click(self):
        actor = self.scene.get_actor('GOBLIT')
        if actor:
            actor.move_to(
                self.pos,
                on_move_end=lambda: self.take(actor),
                strict=False,
                exclusive=True
            )

    def take(self, actor):
        """Actually pick up the thing."""
        actor.face(self)
        inventory.add(self.item)
        self.scene.unspawn_object(self)

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

    def get_use_action(self, obj):
        """Return an action if this item is usable with obj."""
        # Action('Use %s with %s' % (self.name, obj), lambda: print("Using %s with %s" % (self.name, obj)))
        return None

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
kettle = Item('kettle')


class Inventory:

    item_bg = None

    @classmethod
    def load(cls):
        """Load common item sprites."""
        if cls.item_bg:
            return
        cls.item_bg = load_image('item-bg')
        cls.item_bg_on = load_image('item-bg-on')

    def __init__(self, items=[]):
        self.items = items
        self.selected = None

    def add(self, item):
        """Add an item to the inventory."""
        self.items.append(item)

    def remove(self, item):
        if item is self.selected:
            self.selected = None
        self.items.remove(item)

    def layout(self):
        """Iterate items in a grid layout as (x, y, item) tuples"""
        x = 0
        y = 0
        for item in self.items:
            yield x, y, item
            x += 1
            if x == 12:
                x = 0
                y += 1

    def screen_layout(self, grid):
        """Iterate items in a grid layout as (x, y, item) tuples.

        Unlike layout() above, the coordinates are in screen space.

        """
        for x, y, item in grid:
            x = 21 + 78 * x
            y = 460 + 78 * y
            yield x, y, item

    def full_grid(self):
        return ((x, y, None) for y in range(2) for x in range(12))

    def grid_bounds(self):
        """Iterate over the inventory as (rect, item) pairs."""
        for x, y, item in self.screen_layout(self.layout()):
            yield Rect(x, y, 60, 60), item

    def item_for_pos(self, pos):
        for r, item in self.grid_bounds():
            if r.collidepoint(pos):
                return item

    def select(self, item):
        if self.selected is item:
            self.selected = None
        else:
            self.selected = item

    def deselect(self):
        self.selected = None

    def draw(self, screen):
        self.load()
        for x, y, item in self.screen_layout(self.layout()):
            bg = self.item_bg_on if item is self.selected else self.item_bg
            screen.blit(bg, (x, y))

        for x, y, item in self.screen_layout(self.layout()):
            im = item.icon
            r = im.get_rect()
            r.center = (x + 30, y + 30)
            screen.blit(im, r)


inventory = Inventory()
