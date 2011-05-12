#!/usr/bin/python
# -*- coding: utf-8 -*-

u"""
TileMap loader for python for Tiled, a generic tile map editor
from http://mapeditor.org/ .
It loads the \*.tmx files produced by Tiled.


"""

# Versioning scheme based on: http://en.wikipedia.org/wiki/Versioning#Designating_development_stage
#
#   +-- api change, probably incompatible with older versions
#   |     +-- enhancements but no api change
#   |     |
# major.minor[.build[.revision]]
#                |
#                +-|* 0 for alpha (status)
#                  |* 1 for beta (status)
#                  |* 2 for release candidate
#                  |* 3 for (public) release
#
# For instance:
#     * 1.2.0.1 instead of 1.2-a
#     * 1.2.1.2 instead of 1.2-b2 (beta with some bug fixes)
#     * 1.2.2.3 instead of 1.2-rc (release candidate)
#     * 1.2.3.0 instead of 1.2-r (commercial distribution)
#     * 1.2.3.5 instead of 1.2-r5 (commercial distribution with many bug fixes)

__revision__ = "$Rev: 19 $"
__version__ = "3.0.0." + __revision__[6:-2]
__revision__ = u'$Id: tiledtmxloader.py 13 2011-02-22 19:29:13Z dr0iddr0id@gmail.com $'
__author__ = u'DR0ID_ @ 2009-2011'

if __debug__:
    print __version__
    import sys
    sys.stdout.write(u'%s loading ... \n' % (__name__))
    import time
    _start_time = time.time()

#-------------------------------------------------------------------------------


import sys
from xml.dom import minidom, Node
import StringIO
import os.path


#-------------------------------------------------------------------------------
# TODO: separate resource loading and containment into own class for each graphics lib
#       by doing so, loading the map can be done in the model, loading the graphics resources in the presentation layer
class IImageLoader(object):
    u"""
    Interface for image loading. Depending on the framework used the
    images have to be loaded differently.
    """

    def load_image(self, filename, colorkey=None): # -> image
        u"""
        Load a single image.

        :Parameters:
            filename : string
                Path to the file to be loaded.
            colorkey : tuple
                The (r, g, b) color that should be used as colorkey (or magic color).
                Default: None

        :rtype: image

        """
        raise NotImplementedError(u'This should be implemented in a inherited class')

    def load_image_file_like(self, file_like_obj, colorkey=None): # -> image
        u"""
        Load a image from a file like object.

        :Parameters:
            file_like_obj : file
                This is the file like object to load the image from.
            colorkey : tuple
                The (r, g, b) color that should be used as colorkey (or magic color).
                Default: None

        :rtype: image
        """
        raise NotImplementedError(u'This should be implemented in a inherited class')

    def load_image_parts(self, filename, margin, spacing, tile_width, tile_height, colorkey=None): #-> [images]
        u"""
        Load different tile images from one source image.

        :Parameters:
            filename : string
                Path to image to be loaded.
            margin : int
                The margin around the image.
            spacing : int
                The space between the tile images.
            tile_width : int
                The width of a single tile.
            tile_height : int
                The height of a single tile.
            colorkey : tuple
                The (r, g, b) color that should be used as colorkey (or magic color).
                Default: None

        Luckily that iteration is so easy in python::

            ...
            w, h = image_size
            for y in xrange(margin, h, tile_height + spacing):
                for x in xrange(margin, w, tile_width + spacing):
                    ...

        :rtype: a list of images
        """
        raise NotImplementedError(u'This should be implemented in a inherited class')

#-------------------------------------------------------------------------------
class ImageLoaderPygame(IImageLoader):
    u"""
    Pygame image loader.

    It uses an internal image cache. The methods return Surface.

    :Undocumented:
        pygame
    """


    def __init__(self):
        self.pygame = __import__('pygame')
        self._img_cache = {} # {name: surf}

    def load_image(self, filename, colorkey=None):
        img = self._img_cache.get(filename, None)
        if img is None:
            img = self.pygame.image.load(filename)
            self._img_cache[filename] = img
        if colorkey:
            img.set_colorkey(colorkey, self.pygame.RLEACCEL)
        return img

    def load_image_part(self, filename, x, y, w, h, colorkey=None):
        source_img = self.load_image(filename, colorkey)
        ## ISSUE 4:
        ##      The following usage seems to be broken in pygame (1.9.1.):
        ##      img_part = self.pygame.Surface((tile_width, tile_height), 0, source_img)
        img_part = self.pygame.Surface((w, h), source_img.get_flags(), source_img.get_bitsize())
        source_rect = self.pygame.Rect(x, y, w, h)
        img_part.blit(source_img, (0, 0), source_rect)
        if colorkey:
            img_part.set_colorkey(colorkey, self.pygame.RLEACCEL)
        return img_part

    def load_image_parts(self, filename, margin, spacing, tile_width, tile_height, colorkey=None): #-> [images]
        source_img = self.load_image(filename, colorkey)
        w, h = source_img.get_size()
        images = []
        for y in xrange(margin, h, tile_height + spacing):
            for x in xrange(margin, w, tile_width + spacing):
                img_part = self.load_image_part(filename, x, y, tile_width, tile_height, colorkey)
                images.append(img_part)
        return images

    def load_image_file_like(self, file_like_obj, colorkey=None): # -> image
        # pygame.image.load can load from a path and from a file-like object
        # that is why here it is redirected to the other method
        return self.load_image(file_like_obj, colorkey)

#-------------------------------------------------------------------------------
class ImageLoaderPyglet(IImageLoader):
    u"""
    Pyglet image loader.

    It uses an internal image cache. The methods return some form of
    AbstractImage. The resource module is not used for loading the images.

    Thanks to HydroKirby from #pyglet to contribute the ImageLoaderPyglet and the pyglet demo!

    :Undocumented:
        pyglet
    """


    def __init__(self):
        self.pyglet = __import__('pyglet')
        self._img_cache = {} # {name: image}

    def load_image(self, filename, colorkey=None, fileobj=None):
        img = self._img_cache.get(filename, None)
        if img is None:
            if fileobj:
                img = self.pyglet.image.load(filename, fileobj, self.pyglet.image.codecs.get_decoders("*.png")[0])
            else:
                img = self.pyglet.image.load(filename)
            self._img_cache[filename] = img
        return img

    def load_image_part(self, filename, x, y, w, h, colorkey=None):
        image = self.load_image(filename, colorkey)
        img_part = image.get_region(x, y, w, h)
        return img_part


    def load_image_parts(self, filename, margin, spacing, tile_width, tile_height, colorkey=None): #-> [images]
        source_img = self.load_image(filename, colorkey)
        images = []
        # Reverse the map column reading to compensate for pyglet's y-origin.
        for y in xrange(source_img.height - tile_height, margin - tile_height,
            -tile_height - spacing):
            for x in xrange(margin, source_img.width, tile_width + spacing):
                img_part = self.load_image_part(filename, x, y - spacing, tile_width, tile_height)
                images.append(img_part)
        return images

    def load_image_file_like(self, file_like_obj, colorkey=None): # -> image
        # pyglet.image.load can load from a path and from a file-like object
        # that is why here it is redirected to the other method
        return self.load_image(file_like_obj, colorkey, file_like_obj)

#-------------------------------------------------------------------------------
class TileMap(object):
    u"""

    The TileMap holds all the map data.

    :Ivariables:
        orientation : string
            orthogonal or isometric or hexagonal or shifted
        tilewidth : int
            width of the tiles (for all layers)
        tileheight : int
            height of the tiles (for all layers)
        width : int
            width of the map (number of tiles)
        height : int
            height of the map (number of tiles)
        version : string
            version of the map format
        tile_sets : list
            list of TileSet
        properties : dict
            the propertis set in the editor, name-value pairs, strings
        pixel_width : int
            width of the map in pixels
        pixel_height : int
            height of the map in pixels
        layers : list
            list of TileLayer
        map_file_name : dict
            file name of the map
        object_groups : list
            list of :class:MapObjectGroup
        indexed_tiles : dict
            dict containing {gid : (offsetx, offsety, surface} if load() was called
            when drawing just add the offset values to the draw point
        named_layers : dict of string:TledLayer
            dict containing {name : TileLayer}
        named_tile_sets : dict
            dict containing {name : TileSet}

    """


    def __init__(self):
#        This is the top container for all data. The gid is the global id (for a image).
#        Before calling convert most of the values are strings. Some additional
#        values are also calculated, see convert() for details. After calling
#        convert, most values are integers or floats where appropriat.
        u"""
        The TileMap holds all the map data.
        """
        # set through parser
        self.orientation = None
        self.tileheight = 0
        self.tilewidth = 0
        self.width = 0
        self.height = 0
        self.version = 0
        self.tile_sets = [] # TileSet
        self.layers = [] # WorldTileLayer <- what order? back to front (guessed)
        self.indexed_tiles = {} # {gid: (offsetx, offsety, image}
        self.object_groups = []
        self.properties = {} # {name: value}
        # additional info
        self.pixel_width = 0
        self.pixel_height = 0
        self.named_layers = {} # {name: layer}
        self.named_tile_sets = {} # {name: tile_set}
        self.map_file_name = ""
        self._image_loader = None

    def convert(self):
        u"""
        Converts numerical values from strings to numerical values.
        It also calculates or set additional data:
        pixel_width
        pixel_height
        named_layers
        named_tile_sets
        """
        self.tilewidth = int(self.tilewidth)
        self.tileheight = int(self.tileheight)
        self.width = int(self.width)
        self.height = int(self.height)
        self.pixel_width = self.width * self.tilewidth
        self.pixel_height = self.height * self.tileheight
        for layer in self.layers:
            self.named_layers[layer.name] = layer
            layer.opacity = float(layer.opacity)
            layer.x = int(layer.x)
            layer.y = int(layer.y)
            layer.width = int(layer.width)
            layer.height = int(layer.height)
            layer.pixel_width = layer.width * self.tilewidth
            layer.pixel_height = layer.height * self.tileheight
            layer.visible = bool(int(layer.visible))
        for tile_set in self.tile_sets:
            self.named_tile_sets[tile_set.name] = tile_set
            tile_set.spacing = int(tile_set.spacing)
            tile_set.margin = int(tile_set.margin)
            for img in tile_set.images:
                if img.trans:
                    img.trans = (int(img.trans[:2], 16), int(img.trans[2:4], 16), int(img.trans[4:], 16))
        for obj_group in self.object_groups:
            obj_group.x = int(obj_group.x)
            obj_group.y = int(obj_group.y)
            obj_group.width = int(obj_group.width)
            obj_group.height = int(obj_group.height)
            for map_obj in obj_group.objects:
                map_obj.x = int(map_obj.x)
                map_obj.y = int(map_obj.y)
                map_obj.width = int(map_obj.width)
                map_obj.height = int(map_obj.height)

    def load(self, image_loader):
        u"""
        loads all images using a IImageLoadermage implementation and fills up
        the indexed_tiles dictionary.
        The image may have per pixel alpha or a colorkey set.
        """
        self._image_loader = image_loader
        for tile_set in self.tile_sets:
            # do images first, because tiles could reference it
            for img in tile_set.images:
                if img.source:
                    self._load_image_from_source(tile_set, img)
                else:
                    tile_set.indexed_images[img.id] = self._load_image(img)
            # tiles
            for tile in tile_set.tiles:
                for img in tile.images:
                    if not img.content and not img.source:
                        # only image id set
                        indexed_img = tile_set.indexed_images[img.id]
                        self.indexed_tiles[int(tile_set.firstgid) + int(tile.id)] = (0, 0, indexed_img)
                    else:
                        if img.source:
                            self._load_image_from_source(tile_set, img)
                        else:
                            indexed_img = self._load_image(img)
                            self.indexed_tiles[int(tile_set.firstgid) + int(tile.id)] = (0, 0, indexed_img)

    def _load_image_from_source(self, tile_set, a_tile_image):
        # relative path to file
        img_path = os.path.join(os.path.dirname(self.map_file_name), a_tile_image.source)
        tile_width = int(self.tilewidth)
        tile_height = int(self.tileheight)
        if tile_set.tileheight:
            tile_width = int(tile_set.tilewidth)
        if tile_set.tilewidth:
            tile_height = int(tile_set.tileheight)
        offsetx = 0
        offsety = 0
#        if tile_width > self.tilewidth:
#            offsetx = tile_width
        if tile_height > self.tileheight:
            offsety = tile_height - self.tileheight
        idx = 0
        for image in self._image_loader.load_image_parts(img_path, \
                    tile_set.margin, tile_set.spacing, tile_width, tile_height, a_tile_image.trans):
            self.indexed_tiles[int(tile_set.firstgid) + idx] = (offsetx, -offsety, image)
            idx += 1

    def _load_image(self, a_tile_image):
        img_str = a_tile_image.content
        if a_tile_image.encoding:
            if a_tile_image.encoding == u'base64':
                img_str = decode_base64(a_tile_image.content)
            else:
                raise Exception(u'unknown image encoding %s' % a_tile_image.encoding)
        sio = StringIO.StringIO(img_str)
        new_image = self._image_loader.load_image_file_like(sio, a_tile_image.trans)
        return new_image

    def decode(self):
        u"""
        Decodes the TileLayer encoded_content and saves it in decoded_content.
        """
        for layer in self.layers:
            layer.decode()
#-------------------------------------------------------------------------------


class TileSet(object):
    u"""
    A tileset holds the tiles and its images.

    :Ivariables:
        firstgid : int
            the first gid of this tileset
        name : string
            the name of this TileSet
        images : list
            list of TileImages
        tiles : list
            list of Tiles
        indexed_images : dict
            after calling load() it is dict containing id: image
        indexed_tiles : dict
            after calling load() it is a dict containing
            gid: (offsetx, offsety, image) , the image corresponding to the gid
        spacing : int
            the spacing between tiles
        marging : int
            the marging of the tiles
        properties : dict
            the propertis set in the editor, name-value pairs
        tilewidth : int
            the actual width of the tile, can be different from the tilewidth of the map
        tilehight : int
            the actual hight of th etile, can be different from the tilehight of the  map

    """

    def __init__(self):
        self.firstgid = 0
        self.name = None
        self.images = [] # TileImage
        self.tiles = [] # Tile
        self.indexed_images = {} # {id:image}
        self.indexed_tiles = {} # {gid: (offsetx, offsety, image} <- actually in map data
        self.spacing = 0
        self.margin = 0
        self.properties = {}
        self.tileheight = 0
        self.tilewidth = 0

#-------------------------------------------------------------------------------

class TileImage(object):
    u"""
    An image of a tile or just an image.

    :Ivariables:
        id : int
            id of this image (has nothing to do with gid)
        format : string
            the format as string, only 'png' at the moment
        source : string
            filename of the image. either this is set or the content
        encoding : string
            encoding of the content
        trans : tuple of (r,g,b)
            the colorkey color, raw as hex, after calling convert just a (r,g,b) tuple
        properties : dict
            the propertis set in the editor, name-value pairs
        image : TileImage
            after calling load the pygame surface
    """

    def __init__(self):
        self.id = 0
        self.format = None
        self.source = None
        self.encoding = None # from <data>...</data>
        self.content = None # from <data>...</data>
        self.image = None
        self.trans = None
        self.properties = {} # {name: value}

#-------------------------------------------------------------------------------

class Tile(object):
    u"""
    A single tile.

    :Ivariables:
        id : int
            id of the tile gid = TileSet.firstgid + Tile.id
        images : list of :class:TileImage
            list of TileImage, either its 'id' or 'image data' will be set
        properties : dict of name:value
            the propertis set in the editor, name-value pairs
    """

    def __init__(self):
        self.id = 0
        self.images = [] # uses TileImage but either only id will be set or image data
        self.properties = {} # {name: value}

#-------------------------------------------------------------------------------

class TileLayer(object):
    u"""
    A layer of the world.

    :Ivariables:
        x : int
            position of layer in the world in number of tiles (not pixels)
        y : int
            position of layer in the world in number of tiles (not pixels)
        width : int
            number of tiles in x direction
        height : int
            number of tiles in y direction
        pixel_width : int
            width of layer in pixels
        pixel_height : int
            height of layer in pixels
        name : string
            name of this layer
        opacity : float
            float from 0 (full transparent) to 1.0 (opaque)
        decoded_content : list
            list of graphics id going through the map::

                e.g [1, 1, 1, ]
                where decoded_content[0] is (0,0)
                      decoded_content[1] is (1,0)
                      ...
                      decoded_content[1] is (width,0)
                      decoded_content[1] is (0,1)
                      ...
                      decoded_content[1] is (width,height)

                usage: graphics id = decoded_content[tile_x + tile_y * width]
        content2D : list
            list of list, usage: graphics id = content2D[x][y]

    """

    def __init__(self):
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.pixel_width = 0
        self.pixel_height = 0
        self.name = None
        self.opacity = -1
        self.encoding = None
        self.compression = None
        self.encoded_content = None
        self.decoded_content = []
        self.visible = True
        self.properties = {} # {name: value}
        self.content2D = None

    def decode(self):
        u"""
        Converts the contents in a list of integers which are the gid of the used
        tiles. If necessairy it decodes and uncompresses the contents.
        """
        self.decoded_content = []
        if self.encoded_content:
            s = self.encoded_content
            if self.encoding:
                if self.encoding.lower() == u'base64':
                    s = decode_base64(s)
                elif self.encoding.lower() == u'csv':
                    list_of_lines = s.split()
                    for line in list_of_lines:
                        self.decoded_content.extend(line.split(','))
                    self.decoded_content = map(int, [val for val in self.decoded_content if val])
                    s = ""
                else:
                    raise Exception(u'unknown data encoding %s' % (self.encoding))
            else:
                # in the case of xml the encoded_content already contains a list of integers
                self.decoded_content = map(int, self.encoded_content)
                s = ""
            if self.compression:
                if self.compression == u'gzip':
                    s = decompress_gzip(s)
                elif self.compression == u'zlib':
                    s = decompress_zlib(s)
                else:
                    raise Exception(u'unknown data compression %s' %(self.compression))
        else:
            raise Exception(u'no encoded content to decode')
        for idx in xrange(0, len(s), 4):
            val = ord(str(s[idx])) | (ord(str(s[idx + 1])) << 8) | \
                 (ord(str(s[idx + 2])) << 16) | (ord(str(s[idx + 3])) << 24)
            self.decoded_content.append(val)
        #print len(self.decoded_content)
        # generate the 2D version
        self._gen_2D()

    def _gen_2D(self):
        self.content2D = []
        # generate the needed lists
        for xpos in xrange(self.width):
            self.content2D.append([])
        # fill them
        for xpos in xrange(self.width):
            for ypos in xrange(self.height):
                self.content2D[xpos].append(self.decoded_content[xpos + ypos * self.width])

    def pretty_print(self):
        num = 0
        for y in range(int(self.height)):
            s = u""
            for x in range(int(self.width)):
                s += str(self.decoded_content[num])
                num += 1
            print s

    # def get_visible_tile_range(self, xmin, ymin, xmax, ymax):
        # tile_w = self.pixel_width / self.width
        # tile_h = self.pixel_height / self.height
        # left = int(round(float(xmin) / tile_w)) - 1
        # right = int(round(float(xmax) / tile_w)) + 2
        # top = int(round(float(ymin) / tile_h)) - 1
        # bottom = int(round(float(ymax) / tile_h)) + 2
        # return (left, top, left - right, top - bottom)

    # def get_tiles(self, xmin, ymin, xmax, ymax):
        # tiles = []
        # if self.visible:
            # for ypos in range(ymin, ymax):
                # for xpos in range(xmin, xmax):
                    # try:
                        # img_idx = self.content2D[xpos][ypos]
                        # if img_idx:
                            # tiles.append((xpos, ypos, img_idx))
                    # except IndexError:
                        # pass
        # return tiles

#-------------------------------------------------------------------------------


class MapObjectGroup(object):
    u"""
    Group of objects on the map.

    :Ivariables:
        x : int
            the x position
        y : int
            the y position
        width : int
            width of the bounding box (usually 0, so no use)
        height : int
            height of the bounding box (usually 0, so no use)
        name : string
            name of the group
        objects : list
            list of the map objects

    """

    def __init__(self):
        self.width = 0
        self.height = 0
        self.name = None
        self.objects = []
        self.x = 0
        self.y = 0
        self.properties = {} # {name: value}

#-------------------------------------------------------------------------------

class MapObject(object):
    u"""
    A single object on the map.

    :Ivariables:
        x : int
            x position relative to group x position
        y : int
            y position relative to group y position
        width : int
            width of this object
        height : int
            height of this object
        type : string
            the type of this object
        image_source : string
            source path of the image for this object
        image : :class:TileImage
            after loading this is the pygame surface containing the image
    """
    def __init__(self):
        self.name = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.type = None
        self.image_source = None
        self.image = None
        self.properties = {} # {name: value}

#-------------------------------------------------------------------------------
def decode_base64(in_str):
    u"""
    Decodes a base64 string and returns it.

    :Parameters:
        in_str : string
            base64 encoded string

    :returns: decoded string
    """
    import base64
    return base64.decodestring(in_str)

#-------------------------------------------------------------------------------
def decompress_gzip(in_str):
    u"""
    Uncompresses a gzip string and returns it.

    :Parameters:
        in_str : string
            gzip compressed string

    :returns: uncompressed string
    """
    import gzip
    # gzip can only handle file object therefore using StringIO
    copmressed_stream = StringIO.StringIO(in_str)
    gzipper = gzip.GzipFile(fileobj=copmressed_stream)
    s = gzipper.read()
    gzipper.close()
    return s

#-------------------------------------------------------------------------------
def decompress_zlib(in_str):
    u"""
    Uncompresses a zlib string and returns it.

    :Parameters:
        in_str : string
            zlib compressed string

    :returns: uncompressed string
    """
    import zlib
    s = zlib.decompress(in_str)
    return s
#-------------------------------------------------------------------------------
def printer(obj, ident=''):
    u"""
    Helper function, prints a hirarchy of objects.
    """
    import inspect
    print ident + obj.__class__.__name__.upper()
    ident += '    '
    lists = []
    for name in dir(obj):
        elem = getattr(obj, name)
        if isinstance(elem, list) and name != u'decoded_content':
            lists.append(elem)
        elif not inspect.ismethod(elem):
            if not name.startswith('__'):
                if name == u'data' and elem:
                    print ident + u'data = '
                    printer(elem, ident + '    ')
                else:
                    print ident + u'%s\t= %s' % (name, getattr(obj, name))
    for l in lists:
        for i in l:
            printer(i, ident + '    ')

#-------------------------------------------------------------------------------
class TileMapParser(object):
    u"""
    Allows to parse and decode map files for 'Tiled', a open source map editor
    written in java. It can be found here: http://mapeditor.org/
    """

    def _build_tile_set(self, tile_set_node, world_map):
        tile_set = TileSet()
        self._set_attributes(tile_set_node, tile_set)
        if hasattr(tile_set, "source"):
            tile_set = self._parse_tsx(tile_set.source, tile_set, world_map)
        else:
            tile_set = self._get_tile_set(tile_set_node, tile_set, self.map_file_name)
        world_map.tile_sets.append(tile_set)

    def _parse_tsx(self, file_name, tile_set, world_map):
        # ISSUE 5: the *.tsx file is probably relative to the *.tmx file
        if not os.path.isabs(file_name):
            print "map file name", self.map_file_name
            file_name = self._get_abs_path(self.map_file_name, file_name)
        print "tsx filename: ", file_name
        # would be more elegant to use  "with open(file_name, "rb") as file:" but that is python 2.6
        file = None
        try:
            file = open(file_name, "rb")
            dom = minidom.parseString(file.read())
        finally:
            if file:
                file.close()
        for node in self._get_nodes(dom.childNodes, 'tileset'):
            tile_set = self._get_tile_set(node, tile_set, file_name)
            break;
        return tile_set

    def _get_tile_set(self, tile_set_node, tile_set, base_path):
        for node in self._get_nodes(tile_set_node.childNodes, u'image'):
            self._build_tile_set_image(node, tile_set, base_path)
        for node in self._get_nodes(tile_set_node.childNodes, u'tile'):
            self._build_tile_set_tile(node, tile_set)
        self._set_attributes(tile_set_node, tile_set)
        return tile_set

    def _build_tile_set_image(self, image_node, tile_set, base_path):
        image = TileImage()
        self._set_attributes(image_node, image)
        # id of TileImage has to be set!! -> Tile.TileImage will only have id set
        for node in self._get_nodes(image_node.childNodes, u'data'):
            self._set_attributes(node, image)
            image.content = node.childNodes[0].nodeValue
        image.source = self._get_abs_path(base_path, image.source) # ISSUE 5
        tile_set.images.append(image)

    def _get_abs_path(self, base, relative):
            if os.path.isabs(relative):
                return relative
            if os.path.isfile(base):
                base = os.path.dirname(base)
            return os.path.abspath(os.path.join(base, relative))

    def _build_tile_set_tile(self, tile_set_node, tile_set):
        tile = Tile()
        self._set_attributes(tile_set_node, tile)
        for node in self._get_nodes(tile_set_node.childNodes, u'image'):
            self._build_tile_set_tile_image(node, tile)
        tile_set.tiles.append(tile)

    def _build_tile_set_tile_image(self, tile_node, tile):
        tile_image = TileImage()
        self._set_attributes(tile_node, tile_image)
        for node in self._get_nodes(tile_node.childNodes, u'data'):
            self._set_attributes(node, tile_image)
            tile_image.content = node.childNodes[0].nodeValue
        tile.images.append(tile_image)

    def _build_layer(self, layer_node, world_map):
        layer = TileLayer()
        self._set_attributes(layer_node, layer)
        for node in self._get_nodes(layer_node.childNodes, u'data'):
            self._set_attributes(node, layer)
            if layer.encoding:
                layer.encoded_content = node.lastChild.nodeValue
            else:
                #print 'has childnodes', node.hasChildNodes()
                layer.encoded_content = []
                for child in node.childNodes:
                    if child.nodeType == Node.ELEMENT_NODE and child.nodeName == "tile":
                        val = child.attributes["gid"].nodeValue
                        #print child, val
                        layer.encoded_content.append(val)
        world_map.layers.append(layer)

    def _build_world_map(self, world_node):
        world_map = TileMap()
        self._set_attributes(world_node, world_map)
        if world_map.version != u"1.0":
            raise Exception(u'this parser was made for maps of version 1.0, found version %s' % world_map.version)
        for node in self._get_nodes(world_node.childNodes, u'tileset'):
            self._build_tile_set(node, world_map)
        for node in self._get_nodes(world_node.childNodes, u'layer'):
            self._build_layer(node, world_map)
        for node in self._get_nodes(world_node.childNodes, u'objectgroup'):
            self._build_object_groups(node, world_map)
        return world_map

    def _build_object_groups(self, object_group_node, world_map):
        object_group = MapObjectGroup()
        self._set_attributes(object_group_node,  object_group)
        for node in self._get_nodes(object_group_node.childNodes, u'object'):
            tiled_object = MapObject()
            self._set_attributes(node, tiled_object)
            for img_node in self._get_nodes(node.childNodes, u'image'):
                tiled_object.image_source = img_node.attributes[u'source'].nodeValue
            object_group.objects.append(tiled_object)
        world_map.object_groups.append(object_group)

    #-- helpers --#
    def _get_nodes(self, nodes, name):
        for node in nodes:
            if node.nodeType == Node.ELEMENT_NODE and node.nodeName == name:
                yield node

    def _set_attributes(self, node, obj):
        attrs = node.attributes
        for attr_name in attrs.keys():
            setattr(obj, attr_name, attrs.get(attr_name).nodeValue)
        self._get_properties(node, obj)


    def _get_properties(self, node, obj):
        props = {}
        for properties_node in self._get_nodes(node.childNodes, u'properties'):
            for property_node in self._get_nodes(properties_node.childNodes, u'property'):
                try:
                    props[property_node.attributes[u'name'].nodeValue] = property_node.attributes[u'value'].nodeValue
                except KeyError:
                    props[property_node.attributes[u'name'].nodeValue] = property_node.lastChild.nodeValue
        obj.properties.update(props)


    #-- parsers --#
    def parse(self, file_name):
        u"""
        Parses the given map. Does no decoding nor loading the data.
        :return: instance of TileMap
        """
        # would be more elegant to use  "with open(file_name, "rb") as file:" but that is python 2.6
        self.map_file_name = os.path.abspath(file_name)
        file = None
        try:
            file = open(self.map_file_name, "rb")
            dom = minidom.parseString(file.read())
        finally:
            if file:
                file.close()
        for node in self._get_nodes(dom.childNodes, 'map'):
            world_map = self._build_world_map(node)
            break
        world_map.map_file_name = self.map_file_name
        world_map.convert()
        return world_map

    def parse_decode(self, file_name):
        u"""
        Parses the map but additionally decodes the data.
        :return: instance of TileMap
        """
        world_map = TileMapParser().parse(file_name)
        world_map.decode()
        return world_map

    def parse_decode_load(self, file_name, image_loader):
        u"""
        Parses the data, decodes them and loads the images using the image_loader.
        :return: instance of TileMap
        """
        world_map = self.parse_decode(file_name)
        world_map.load(image_loader)
        return world_map

#-------------------------------------------------------------------------------

class RendererPygame(object):

# TODO: rename variables
# TODO: paralax scrolling

    class Sprite(object):
        def __init__(self, image, rect, source_rect=None, flags=0):
            self.image = image
            self.rect = rect
            self.source_rect = source_rect
            self.flags = flags

    class _Layer(object):
        def __init__(self, layer_id, world_map):
            self._world_map = world_map
            self._layer_id = layer_id
            self.content2D = []
            self.level = 1
            self.collapse(1)

        def collapse(self, level=1):
            self.level = level
            pygame = __import__('pygame')

            self.tilewidth = self._world_map.tilewidth * level
            self.tileheight = self._world_map.tileheight * level
            self.width = int(self._world_map.width / float(level) + 0.5)
            self.height = int(self._world_map.height / float(level) + 0.5)

            layer = self._world_map.layers[self._layer_id]

            # generate the needed lists
            for xpos in xrange(self.width):
                self.content2D.append([None]*self.height)

            # fill them
            for xpos in xrange(self.width):
                for ypos in xrange(self.height):
                    images = []
                    minx = xpos
                    miny = ypos
                    maxx = xpos + self.tilewidth
                    maxy = ypos + self.tileheight
                    flags = 0
                    depth = 0
                    for x in range(level):
                        for y in range(level):
                            orig_x = xpos * level + x
                            orig_y = ypos * level + y
                            try:
                                img_idx = layer.content2D[orig_x][orig_y]
                            except:
                                img_idx = None
                            if img_idx:
                                info = self._world_map.indexed_tiles[img_idx]
                                offx, offy, img = info
                                flags |= img.get_flags()
                                if depth < img.get_bitsize():
                                    depth = img.get_bitsize()
                                if xpos + x - offx < minx:
                                    minx = xpos + x - offx
                                if xpos + x - offx + img.get_width() > maxx:
                                    maxx = xpos + x - offx + img.get_width()
                                if ypos + y - offy < miny:
                                    miny = ypos + y - offy
                                if ypos + y - offy + img.get_height() > maxy:
                                    maxy = ypos + y - offy + img.get_height()
                                images.append(info)
                            else:
                                images.append(None)
                    if level > 1:
                        idx = 0
                        size = (maxx - minx, maxy - miny)
                        if not depth:
                            depth = 32
                        surf = pygame.Surface(size, flags, depth)
                        surf.fill((255, 0, 255))
                        surf.set_colorkey((255, 0, 255), pygame.RLEACCEL)
                        surf = surf.convert_alpha()
                        info = surf.get_width() - self.tilewidth, surf.get_height() - self.tileheight, surf
                        for x in range(level):
                            for y in range(level):
                                orig_info = images[idx]
                                if orig_info:
                                    surf.blit(orig_info[2], (x * self._world_map.tilewidth + info[0] - orig_info[0], y * self._world_map.tileheight + info[1] - orig_info[1]))
                                idx += 1
                    else:
                        idx = layer.content2D[xpos][ypos]
                        info = None
                        if idx:
                            info = self._world_map.indexed_tiles[img_idx]

                    self.content2D[xpos][ypos] = info

    def __init__(self, world_map):
        self._world_map = world_map
        self._cam_offset_x = 0
        self._cam_offset_y = 0
        self._cam_width = 10
        self._cam_height = 10
        self._visible_x_range = []
        self._visible_y_range = []
        self._layers = []
        for idx, layer in enumerate(world_map.layers):
            self._layers.append(self._Layer(idx, world_map))

        self._layer_sprites = {} # {layer_id:[sprites]}

    def add_sprite(self, layer_id, sprite):
        if layer_id not in self._layer_sprites:
            self._layer_sprites[layer_id] = []
        self._layer_sprites[layer_id].append(sprite)

    def add_sprites(self, layer_id, sprites):
        for sprite in sprites:
            self.add_sprite(layer_id, sprite)

    def remove_sprite(self, layer_id, sprite):
        sprites = self._layer_sprites.get(layer_id)
        if sprites is not None and sprite in sprites:
            sprites.remove(sprite)
            if len(sprites) == 0:
                del self._layer_sprites[layer_id]

    def remove_sprites(self, layer_id, sprites):
        for sprite in sprites:
            self.remove_sprite(layer_id, sprite)

    def contains_sprite(self, layer_id, sprite):
        sprites = self._layer_sprites.get(layer_id)
        if sprites is not None:
            return (sprite in sprites)

    def set_camera_position(self, offset_x, offset_y, width, height, margin=0):
        self._cam_offset_x = int(offset_x)
        self._cam_offset_y = int(offset_y)
        self._cam_width = width
        self._cam_height = height
        self._margin = margin + 1

    def get_collapse_level(self, layer_id):
        return self._layers[layer_id].level

    def set_collapse_level(self, layer_id, level):
        level = max(1, level)
        self._layers[layer_id].collapse(level)

    def render_layer(self, surf, layer_id, surf_blit=None, sort_key=lambda spr: spr.rect.y):
        world_layer = self._world_map.layers[layer_id]
        if world_layer.visible:

            # sprites
            spr_idx = 0
            len_sprites = 0
            sprites = self._layer_sprites.get(layer_id)
            if sprites:
                if sort_key:
                    sprites.sort(key=sort_key)
                sprite = sprites[0]
                len_sprites = len(sprites)

            layer = self._layers[layer_id]

            tile_w = layer.tilewidth
            tile_h = layer.tileheight
            self._cam_offset_x += world_layer.x
            self._cam_offset_y += world_layer.y
            left = int(round(float(self._cam_offset_x) / tile_w)) - self._margin
            right = int(round(float(self._cam_offset_x + self._cam_width) / tile_w)) + self._margin + 1
            top = int(round(float(self._cam_offset_y) / tile_h)) - self._margin
            bottom = int(round(float(self._cam_offset_y + self._cam_height) / tile_h)) + self._margin + 1
            left = max(left, 0)
            right = min(right, layer.width)
            top = max(top, 0)
            bottom = min(bottom, layer.height)
            self._visible_x_range = range(left, right)
            self._visible_y_range = range(top, bottom)

            # optimizations
            if surf_blit is None:
                surf_blit = surf.blit
            layer_content2D = layer.content2D
            # self__world_map_indexed_tiles = self._world_map.indexed_tiles
            self__world_map_tilewidth = layer.tilewidth
            self__world_map_tileheight = layer.tileheight
            self__cam_offset_x = self._cam_offset_x
            self__cam_offset_y = self._cam_offset_y

            # render
            for ypos in self._visible_y_range:
                screen_tile_y =(ypos + world_layer.y) * self__world_map_tileheight - self__cam_offset_y
                # draw sprites in this layer
                while spr_idx < len_sprites and screen_tile_y < sprite.rect.y - self__cam_offset_y <= screen_tile_y + self__world_map_tileheight:
                    surf_blit(sprite.image, sprite.rect.move(-self__cam_offset_x, -self__cam_offset_y - sprite.rect.height), sprite.source_rect, sprite.flags)
                    spr_idx += 1
                    if spr_idx < len_sprites:
                        sprite = sprites[spr_idx]
                # next line of the map
                for xpos in self._visible_x_range:
                    img_idx = layer_content2D[xpos][ypos]
                    if img_idx:
                        # get the actual image and its offset
                        offx, offy, screen_img = img_idx #self__world_map_indexed_tiles[img_idx]
                        # add offset in number of tiles
                        pos = (xpos + world_layer.x) * self__world_map_tilewidth - self__cam_offset_x + offx, screen_tile_y + offy
                        # draw image at right position using its offset
                        surf_blit(screen_img, pos)

    # def set_layer_paralax_factor(layer_id, factor_x, factor_y=None, center_x=0, center_y=0):
        # self._world_map[layer_id].paralax_factor_x = factor_x
        # if paralax_factor_y:
            # self._world_map[layer_id].paralax_factor_y = factor_y
        # else:
            # self._world_map[layer_id].paralax_factor_y = factor_x
        # self._world_map[layer_id].paralax_cemter_x = center_x
        # self._world_map[layer_id].paralax_cemter_y = center_y


#-------------------------------------------------------------------------------
def demo_pygame(file_name):
    pygame = __import__('pygame')

    # parser the map (it is done here to initialize the window the same size as the map if it is small enough)
    world_map = TileMapParser().parse_decode(file_name)

    # init pygame and set up a screen
    pygame.init()
    pygame.display.set_caption("tiledtmxloader - " + file_name)
    screen_width = min(1024, world_map.pixel_width)
    screen_height = min(768, world_map.pixel_height)
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF)

    # load the images using pygame
    image_loader = ImageLoaderPygame()
    world_map.load(image_loader)
    #printer(world_map)

    # prepare map rendering
    assert world_map.orientation == "orthogonal"
    renderer = RendererPygame(world_map)

    # cam_offset is for scrolling
    cam_offset_x = 0
    cam_offset_y = 0

    # variables
    frames_per_sec = 60.0
    clock = pygame.time.Clock()
    running = True
    draw_obj = True
    show_message = True
    font = pygame.font.Font(None, 15)
    s = "Frames Per Second: 0.0"
    message = font.render(s, 0, (255,255,255), (0, 0, 0)).convert()

    # for timed fps update
    pygame.time.set_timer(pygame.USEREVENT, 1000)

    # add additional sprites
    num_sprites = 1
    my_sprites = []
    for i in range(num_sprites):
        j = num_sprites - i
        image = pygame.Surface((20, j*40.0/num_sprites+10))
        image.fill(((255+200*j)%255, (2*j+255)%255, (5*j)%255))
        sprite = RendererPygame.Sprite(image, image.get_rect())
        my_sprites.append(sprite)
    # renderer.add_sprites(1, my_sprites)

    # optimizations
    layer_range = range(len(world_map.layers))
    num_keys = [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]
    clock_tick = clock.tick
    pygame_event_get = pygame.event.get
    pygame_key_get_pressed = pygame.key.get_pressed
    renderer_render_layer = renderer.render_layer
    renderer_set_camera_position = renderer.set_camera_position
    pygame_display_flip = pygame.display.flip

    # mainloop
    while running:
        dt = clock_tick()#60.0)

        # event handling
        for event in pygame_event_get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    print "fps:", clock.get_fps()
                    show_message = not show_message
                    print "show info:", show_message
                    # print "visible range x:", renderer._visible_x_range
                    # print "visible range y:", renderer._visible_y_range
                elif event.key == pygame.K_F2:
                    draw_obj = not draw_obj
                    print "show objects:", draw_obj
                elif event.key == pygame.K_w:
                    cam_offset_y -= world_map.tileheight
                elif event.key == pygame.K_s:
                    cam_offset_y += world_map.tileheight
                elif event.key == pygame.K_d:
                    cam_offset_x += world_map.tilewidth
                elif event.key == pygame.K_a:
                    cam_offset_x -= world_map.tilewidth
                elif event.key in num_keys:
                    # find out which layer to manipulate
                    idx = num_keys.index(event.key)
                    # make sure this layer exists
                    if idx < len(world_map.layers):
                        if event.mod & pygame.KMOD_CTRL:
                            # collapse
                            renderer.set_collapse_level(idx, max(renderer.get_collapse_level(idx) - 1, 1))
                            print "layer has collapse level:", renderer.get_collapse_level(idx)
                        elif event.mod & pygame.KMOD_SHIFT:
                            # uncollapse
                            renderer.set_collapse_level(idx, renderer.get_collapse_level(idx) + 1)
                            print "layer has collapse level:", renderer.get_collapse_level(idx)
                        elif event.mod & pygame.KMOD_ALT:
                            # hero sprites
                            if renderer.contains_sprite(idx, my_sprites[0]):
                                renderer.remove_sprites(idx, my_sprites)
                                print "removed hero sprites from layer", idx
                            else:
                                renderer.add_sprites(idx, my_sprites)
                                print "added hero sprites to layer", idx
                        else:
                            # visibility
                            world_map.layers[idx].visible = not world_map.layers[idx].visible
                            print "layer", idx, "visible:", world_map.layers[idx].visible
                    else:
                        print "layer", idx, " does not exist on this map!"
            elif event.type == pygame.USEREVENT:
                if show_message:
                    s = "Number of layers: %i (use 0-9 to toggle)   F1-F2 for other functions   Frames Per Second: %.2f" % (len(world_map.layers), clock.get_fps())
                    message = font.render(s, 0, (255,255,255), (0,0,0)).convert()

        pressed = pygame_key_get_pressed()

        # The speed is 3 by default.
        # When left Shift is held, the speed increases.
        # The speed interpolates based on time passed, so the demo navigates
        # at a reasonable pace even on huge maps.
        speed = (3.0 + pressed[pygame.K_LSHIFT] * 12.0) * (dt / frames_per_sec)

        # cam movement
        if pressed[pygame.K_DOWN]:
            cam_offset_y += speed
        if pressed[pygame.K_UP]:
            cam_offset_y -= speed
        if pressed[pygame.K_LEFT]:
            cam_offset_x -= speed
        if pressed[pygame.K_RIGHT]:
            cam_offset_x += speed

        # update sprites position
        for i, spr in enumerate(my_sprites):
            spr.rect.center = cam_offset_x + 1.0*num_sprites*i/num_sprites + screen_width // 2 , cam_offset_y + i * 3 + screen_height // 2

        # adjust camera according the keypresses
        renderer_set_camera_position(cam_offset_x, cam_offset_y, screen_width, screen_height, 3)

        # clear screen, might be left out if every pixel is redrawn anyway
        screen.fill((0,0,0))

        # render the map
        for id in layer_range:
            renderer_render_layer(screen, id, screen.blit)

        # map objects
        if draw_obj:
            for obj_group in world_map.object_groups:
                goffx = obj_group.x
                goffy = obj_group.y
                for map_obj in obj_group.objects:
                    size = (map_obj.width, map_obj.height)
                    if map_obj.image_source:
                        surf = pygame.image.load(map_obj.image_source)
                        surf = pygame.transform.scale(surf, size)
                        screen.blit(surf, (goffx + map_obj.x - cam_offset_x, goffy + map_obj.y - cam_offset_y))
                    else:
                        r = pygame.Rect((goffx + map_obj.x - cam_offset_x, goffy + map_obj.y - cam_offset_y), size)
                        pygame.draw.rect(screen, (255, 255, 0), r, 1)
                        text_img = font.render(map_obj.name, 1, (255, 255, 0))
                        screen.blit(text_img, r.move(1, 2))

        if show_message:
            screen.blit(message, (0,0))

        pygame_display_flip()

#-------------------------------------------------------------------------------
# TODO:
 # - pyglet demo: redo same as for pygame demo, better rendering
 # - test if object gid is already read in and resolved


#-------------------------------------------------------------------------------

def demo_pyglet(file_name):
    """Thanks to: HydroKirby from #pyglet on freenode.org

    Loads and views a map using pyglet.

    Holding the arrow keys will scroll along the map.
    Holding the left shift key will make you scroll faster.
    Pressing the escape key ends the application.

    TODO:
    Maybe use this to put topleft as origin:

        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(0.0, (double)mTarget->w, (double)mTarget->h, 0.0, -1.0, 1.0);

    """

    import pyglet
    from pyglet.gl import glTranslatef, glLoadIdentity

    world_map = TileMapParser().parse_decode(file_name)
    # delta is the x/y position of the map view.
    # delta is a list because it can be accessed from the on_draw function.
    # This list can be used within the update method.
    delta = [0.0, 0.0]
    frames_per_sec = 1.0 / 60.0
    window = pyglet.window.Window(640, 480)

    @window.event
    def on_draw():
        window.clear()
        # Reset the "eye" back to the default location.
        glLoadIdentity()
        # Move the "eye" to the current location on the map.
        glTranslatef(delta[0], delta[1], 0.0)
        # TODO: [21:03]	thorbjorn: DR0ID_: You can generally determine the range of tiles that are visible before your drawing loop, which is much faster than looping over all tiles and checking whether it is visible for each of them.
        # [21:06]	DR0ID_: probably would have to rewrite the pyglet demo to use a similar render loop as you mentioned
        # [21:06]	thorbjorn: Yeah.
        # [21:06]	DR0ID_: I'll keep your suggestion in mind, thanks
        # [21:06]	thorbjorn: I haven't written a specific OpenGL renderer yet, so not sure what's the best approach for a tile map.
        # [21:07]	thorbjorn: Best to create a single texture with all your tiles, bind it, set up your vertex arrays and fill it with the coordinates of the tiles currently on the screen, and then let OpenGL draw the bunch.
        # [21:08]	DR0ID_: for each layer?
        # [21:08]	DR0ID_: yeah, probably a good approach
        # [21:09]	thorbjorn: Ideally for all layers at the same time, if you don't have to draw anything in between.
        # [21:09]	DR0ID_: well, the NPC and other dynamic things need to be drawn in between, right?
        # [21:09]	thorbjorn: Right, so maybe once for the bottom layers, then your complicated stuff, and then another time for the layers on top.

        batch.draw()

    keys = pyglet.window.key.KeyStateHandler()
    window.push_handlers(keys)
    world_map.load(ImageLoaderPyglet())

    def update(dt):
        # The speed is 3 by default.
        # When left Shift is held, the speed increases.
        # The speed interpolates based on time passed, so the demo navigates
        # at a reasonable pace even on huge maps.
        speed = (3.0 + keys[pyglet.window.key.LSHIFT] * 6.0) * \
                (dt / frames_per_sec)
        if keys[pyglet.window.key.LEFT]:
            delta[0] += speed
        if keys[pyglet.window.key.RIGHT]:
            delta[0] -= speed
        if keys[pyglet.window.key.UP]:
            delta[1] -= speed
        if keys[pyglet.window.key.DOWN]:
            delta[1] += speed

    # Generate the graphics for every visible tile.
    batch = pyglet.graphics.Batch()
    sprites = []
    for group_num, layer in enumerate(world_map.layers):
        if layer.visible is False:
            continue
        group = pyglet.graphics.OrderedGroup(group_num)
        for ytile in xrange(layer.height):
            # To compensate for pyglet's upside-down y-axis, the Sprites are
            # placed in rows that are backwards compared to what was loaded
            # into the map. The next operation puts all rows upside-down.
            for xtile in xrange(layer.width):
                #layer.content2D[xtile].reverse()
                image_id = layer.content2D[xtile][ytile]
                if image_id:
                    # o_x and o_y are offsets. They are not helpful here.
                    o_x, o_y, image_file = world_map.indexed_tiles[image_id]
                    sprites.append(pyglet.sprite.Sprite(image_file,
                        world_map.tilewidth * xtile,
                        world_map.tileheight * (layer.height - ytile),
                        batch=batch, group=group))

    pyglet.clock.schedule_interval(update, frames_per_sec)
    pyglet.app.run()


#-------------------------------------------------------------------------------
def main():

    args = sys.argv[1:]
    if len(args) != 2:
        #print 'usage: python test.py mapfile.tmx [pygame|pyglet]'
        print('usage: python %s your_map.tmx [pygame|pyglet]' % \
            os.path.basename(__file__))
        return

    if args[1] == 'pygame':
        demo_pygame(args[0])
    elif args[1] == 'pyglet':
        demo_pyglet(args[0])
    else:
        print 'missing framework, usage: python test.py mapfile.tmx [pygame|pyglet]'
        sys.exit(-1)

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()


if __debug__:
    _dt = time.time() - _start_time
    sys.stdout.write(u'%s loaded: %fs \n' % (__name__, _dt))
