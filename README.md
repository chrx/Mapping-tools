Mapping Tools
===

Tools to support development of maps and graphs using .tmx files created with the [Tiled Map Editor](http://www.mapeditor.org).


generate_navigation.py
---

A navigation graph generator that parses a graph from an object layer in a .tmx file.

* Requires a tile layer named "Map" containing tiles with the property "collision=1" if they are not passable 
* Requires an object layer named "Navigation" containing the navigation points. 
* A .plist file will be created that joins each point up to its nearest neighbours where possible.

usage: python generate_navigation.py *input.tmx* *output.plist*

Originally created in 2011 by Chris Page, [christophator.com](http://blog.christophator.com)