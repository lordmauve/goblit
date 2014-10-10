from copy import copy
from pygame import Rect
from .loaders import load_image
from .actions import Action
from collections import defaultdict


class SceneItem:
    """Base class for an item that is visible in the scene.

    This wraps an underlying item.

    """
    # Z-coordinate is always behind other items
    z = 0

    def __init__(self, scene, item, pos):
        self.scene = scene
        self.item = item
        self.pos = pos

    @property
    def name(self):
        return self.item.name

    @name.setter
    def name(self, v):
        self.item.name = v

    def use_actions(self, item):
        """Subclasses can implement this to define custom actions.

        :param Item item: Item that will be used with this object.
        :returns: list of Action

        """
        return []

    def click_actions(self):
        """Get actions for the given object.

        Only one will actually be used; therefore ensure that operations that
        do things go above purely aesthetic ones.

        """
        return [Action('Look at %s' % self.name)]

    def give_item(self, actor):
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


class FloorItem(SceneItem):
    """An item that is lying on the floor."""
    # Z-coordinate is always behind other items
    z = 0

    def floor_pos(self):
        return self.pos

    def click_actions(self):
        """Floor items can be picked up."""
        return (
            [Action('Pick up %s' % self.name, self.pick_up)] +
            super().click_actions()
        )

    def pick_up(self):
        actor = self.scene.get_actor('GOBLIT')
        if actor:
            actor.move_to(
                self.pos,
                on_move_end=lambda: self.give_item(actor),
                strict=False,
                exclusive=True
            )


class PointItem(SceneItem):
    def __init__(self, scene, item, pos, navpoint):
        super().__init__(scene, item, pos)
        self.navpoint = navpoint

    def floor_pos(self):
        return self.scene.navpoints[self.navpoint]

    def click_actions(self):
        """Floor items can be picked up."""
        return (
            [Action('Take %s' % self.name, self.take)] +
            super().click_actions()
        )

    def take(self):
        actor = self.scene.get_actor('GOBLIT')
        if actor:
            actor.move_to(
                self.navpoint,
                on_move_end=lambda: self.give_item(actor)
            )


class ItemDict(defaultdict):
    def __missing__(self, key):
        return Item(key)


class Item:
    """Inventory item.

    Can also be spawned into the scene.

    """

    # Registry of all items
    items = ItemDict()

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
        if item in self.items:
            item = copy(item)
        self.items.append(item)

    def remove(self, item):
        """Remove item from inventory."""
        if item is self.selected:
            self.selected = None
        self.items.remove(item)

    def gain(self, item_name):
        """Add the item wih the given name to the inventory."""
        i = Item.items[item_name]
        self.add(i)

    def lose(self, item_name):
        """Take the item wih the given name from the inventory.

        Raises ValueError if the player is not holding that item.

        """
        i = Item.items[item_name]
        if i not in self.items:
            raise ValueError("Player does not have %s" % item_name)
        self.remove(i)

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
