#!/usr/bin/env python

u"""
Navigation map creator for Tiled maps. Requires a tmx file with a "Map" tile layer
containing tiles with the property "collision=1" if they are not passable and an 
object layer called "Navigation" containing the navigation points. A plist will be 
created that joins each point up where possible

"""

__author__ = u'Chrx @ 2011-10-03'

import os
import sys
import plistlib
import tiledtmxloader
from euclid import *

def tileCoordForPosition(tileMap, position):
    return Point2(position.x / tileMap.tilewidth, position.y / tileMap.tileheight)

def convertTiledPositionToCocosPosition(tileMap, position):
    return Point2(position.x, tileMap.height-position.y-1)

def tileCoordForObject(tileMap, object):
    return tileCoordForPosition(tileMap, Vector2(object.x, object.y))

def findClosestCell(candidateCells, targetCell):
    currentCandidate=None

    for candidate in candidateCells:
        if currentCandidate is None:
            currentCandidate=candidate
        elif targetCell.distance(candidate) < targetCell.distance(currentCandidate):
            currentCandidate=candidate
                
    return currentCandidate

def canSeeCellFromCell(tileMap, fromCell, toCell, collisionTiles):
    x0=fromCell.x
    y0=fromCell.y
    x1=toCell.x
    y1=toCell.y
    
    dx=abs(x1-x0)
    dy=abs(y1-y0)
    x=x0
    y=y0
    n=1+dx+dy
    
    xinc=1 if x1>x0 else -1
    yinc=1 if y1>y0 else -1
    
    error=dx-dy
    dx=dx*2
    dy=dy*2
    
    while n>0:
        
        gid=tileMap.layers[1].content2D[x][y]
        
        if gid and collisionTiles.count(gid)>0:
            return False
                
        if error>0:
            x=x+xinc
            error=error-dy
        else:
            y=y+yinc
            error=error+dx
        
        n=n-1

    return True

def findNextX(tileMap, objectGroupIndex, target):
    #Y is the same and next.x> target.x
    
    candidateCells=[]
    targetCell=tileCoordForObject(tileMap, target)
    
    for object in tileMap.object_groups[objectGroupIndex].objects:
        
        objectCell=tileCoordForObject(tileMap, object)
        
        if objectCell.y==targetCell.y and objectCell.x>targetCell.x:
            candidateCells.append(objectCell)

    return findClosestCell(candidateCells, targetCell)


def findPrevX(tileMap, objectGroupIndex, target):
    #Y is the same and next.x < target.x
    
    candidateCells=[]
    targetCell=tileCoordForObject(tileMap, target)
    
    for object in tileMap.object_groups[objectGroupIndex].objects:
        
        objectCell=tileCoordForObject(tileMap, object)
        
        if objectCell.y==targetCell.y and objectCell.x<targetCell.x:
            candidateCells.append(objectCell)

    return findClosestCell(candidateCells, targetCell)


def findNextY(tileMap, objectGroupIndex, target):
    #X is the same and next.y < target.y
    
    candidateCells=[]
    targetCell=tileCoordForObject(tileMap, target)
    
    for object in tileMap.object_groups[objectGroupIndex].objects:
        
        objectCell=tileCoordForObject(tileMap, object)
        
        if objectCell.x==targetCell.x and objectCell.y<targetCell.y:
            candidateCells.append(objectCell)

    return findClosestCell(candidateCells, targetCell)

def findPrevY(tileMap, objectGroupIndex, target):
    #X is the same and next.y > target.y
    
    candidateCells=[]
    targetCell=tileCoordForObject(tileMap, target)
    
    for object in tileMap.object_groups[objectGroupIndex].objects:
        
        objectCell=tileCoordForObject(tileMap, object)
        
        if objectCell.x==targetCell.x and objectCell.y>targetCell.y:
            candidateCells.append(objectCell)

    return findClosestCell(candidateCells, targetCell)

args = sys.argv[1:]

if len(args) != 2:
    print "usage: python %s map.tmx nav.plist" % os.path.basename(__file__)
else:
	
	mapFile=args[0]
	plistFile=args[1]
	
	map = tiledtmxloader.TileMapParser().parse_decode(mapFile)
	print "processing %sx%s cells at %sx%s px" % (map.width, map.height, map.tilewidth, map.tileheight)

	layerIndex=None
	mapIndex=None

	for index in xrange(len(map.object_groups)):
	    if map.object_groups[index].name.lower()=="navigation":
	        layerIndex=index
	        break

	for index in xrange(len(map.layers)):
	    if map.layers[index].name.lower()=="map":
	        mapIndex=index
	        break

	print "Found navigation layer at index", layerIndex
	print "Found map layer at index", mapIndex

	if (layerIndex and mapIndex):

		collisionTiles=[]

		for tile in map.tile_sets[0].tiles:
		    if tile.properties["collision"]=="1":
		        collisionTiles.append(int(tile.id) + 1)

		plist = dict()

		for object in map.object_groups[layerIndex].objects:
		    target = tileCoordForPosition(map, object)
		    cells=[]
		    printCells=[]
    
		    cell=findNextX(map, layerIndex, object)
    
		    if cell is not None:
		        if canSeeCellFromCell(map, target, cell, collisionTiles):
		            cells.append(cell)

		    cell=findNextY(map, layerIndex, object)
		    if cell is not None:
		        if canSeeCellFromCell(map, target, cell, collisionTiles):
		            cells.append(cell)

		    cell=findPrevX(map, layerIndex, object)
		    if cell is not None:
		        if canSeeCellFromCell(map, target, cell, collisionTiles):
		            cells.append(cell)

		    cell=findPrevY(map, layerIndex, object)
		    if cell is not None:
		        if canSeeCellFromCell(map, target, cell, collisionTiles):
		            cells.append(cell)

		    cocosTarget = convertTiledPositionToCocosPosition(map, target)

		    for cell in cells:
		        cocosCell = convertTiledPositionToCocosPosition(map, cell)
		        printCells.append("{%d,%d}" % (cocosCell.x, cocosCell.y))

			plist["{%d,%d}" % (cocosTarget.x, cocosTarget.y)] = ",".join(printCells)

		plistlib.writePlist(plist, plistFile)
		print "plist containing %d navigation nodes was created" % len(plist)
	
	else:
		if not layerIndex:
			print "Error: missing ""Navigation"" layer"
	
		if not mapIndex:
			print "Error: missing ""Map"" layer"
		
		sys.exit(-1)