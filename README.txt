====================
The Legend of Goblit
====================

An Adventure Stage play for Pyweek 19, by Daniel Pope.

This game was inspired by classic adventure games, but also took inspiration
from single-set stage plays. The competition theme was "One Room" and so
naturally, all of the action is set in the same room.

Installing
----------

You will need Python 3 and Pygame.

There are binaries for Pygame for Python 3:

* https://bitbucket.org/pygame/pygame/downloads - Windows
* https://launchpad.net/~thopiekar/+archive/ubuntu/pygame - Ubuntu

Playing
-------

Everything is point and click, with the left mouse button.

Right mouse button skips, and Escape skips as far as possible.

The game autosaves each time you hit or complete a puzzle.

If you get stuck, the game's full script is in scripts/script.txt. The game
is completely driven from this data, so do not modify it!

On the other hand, if you want to mod it, go ahead. The syntax isn't too
hairy.

Known Bugs
----------

The game is definitely completable if you do it in a single pass, but the
autosaving process may still have bugs, and a restored save game could in some
cases be uncompletable. Delete some or all of the save files in saves/ if you
want to rewind.

Skipping rapidly while in a dialogue can occasionally cause the action to go
out of sync, but this is temporary.

Credits
-------

Art, Story and Programming -
    Daniel Pope
    Pyweek: http://pyweek.org/u/mauve
    Twitter/Facebook: @lordmauve
    Bitbucket: https://bitbucket.com/lordmauve/

Font -
    AJ Paglia
    http://www.ajpaglia.com/
    http://www.1001freefonts.com/roses_are_ff0000.font

Music -
    Sourced from http://freemusicarchive.org/

    "Python" by Rolemusic
    "Wizard House" by AzureFlux
    "Gringo Steele rocks the 40" by Rolemusic
