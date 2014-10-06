import sys

if sys.version_info[:2] < (3, 2):
    sys.exit("Goblit requires Python 3")

try:
    import pygame
except ImportError:
    sys.exit("Goblit requires Pygame 1.9+")

from goblit.__main__ import main
main()

