import os
import types
import weakref

import pygame

from draw_utils import *

__all__ = ['BaseControl', 'Layout', 'GridCtrl', 'HorizontalLayout', 'VerticalLayout', 'ColorCell', 'Spacer', 'ToolPanel', 'StatusBar', 'VerticalLine', 'YesNoDialog',
           'HorizontalLine', 'SliderCtrl', 'SpriteSheetCtrl', 'SpritePreview', 'Label', 'ButtonCtrl', 'SpriteSheet', 'FileDialog', 'ROI', 'TextEntry']

def save_to_conf(f):
    def wrapped(*args, **kwargs):        
        self = args[0]
        value = args[1]
        res = f(*args, **kwargs)
        if self._conf is not None:
            if self._name is not None:
                if isinstance(value, pygame.Color):
                    value = (value.r, value.g, value.b)                              
                setattr(self._conf, "%s_%s" % (self._name, f.__name__), value)
        return res
    return wrapped

def load_from_conf(f):
    def wrapped(*args, **kwargs):        
        self = args[0]
        res = f(*args, **kwargs)
        if self._conf is not None and self._name is not None:
            res2 = getattr(self._conf, "%s_%s" % (self._name, f.__name__), None)
            if res2 is not None:
                return res2

        return res
    return wrapped   

def makes_dirty(f):
    def wrapped(*args, **kwargs):
        res = f(*args, **kwargs)
        self = args[0]
        self._dirty=True
        return res
    return wrapped
  
class Region():
    (   
    ALIGN_LEFT,
    ALIGN_CENTER,
    *_) = range(2)
    def __init__(self, x, y, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._x = x
        self._y = y
        self._width = width
        self._height = height        
        self._layout = None
        self._parent = None

    @property
    def right(self):
        return self.width + self.x    
    @right.setter
    def right(self, value):
        self.x = value - self.width
    @property
    def top(self):
        return self.y
    @top.setter
    def top(self, value):
        self.y = value

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def y(self):
        return self._y

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, val):
        self._x = val

    @y.setter
    def y(self, value):
        self._y = value

    @property
    def height(self):
        return self._height
    @property
    def width(self):
        return self._width

    @property
    def centerx(self):
        return self.x + self.width // 2

    @property
    def centery(self):
        return self.y + self.height // 2

    @property
    def layout(self):
        if self._layout is None:
            return None
        return self._layout()
        
    @layout.setter
    def layout(self, layout):
        if layout is not None:
            self._layout = weakref.ref(layout)
        else:
            self._layout = None

    @property
    def parent(self):
        if callable(self._parent):
            return self._parent()
        return None

    def _set_parent(self, parent):
        if parent is not None:
            self._parent = weakref.ref(parent)
        else:
            self._parent = None            

class BaseGrid():
    def __init__(self, cols, rows, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rows = rows
        self._cols = cols
    
    def grid_index(self, col, row):
        if row > (self._rows-1):
            raise ValueError('row < self._rows-1')
        if col > (self._cols-1):
            raise ValueError('col < self._cols-1')        
        return row + self._rows * col

    def index_to_cell(self, idx):
        col = idx % self._cols
        row = idx // self._cols
        return col, row

    @property
    def rows(self):
        return self._rows

    @property
    def cols(self):
        return self._cols

    def has_cell(self, col, row):
        """ check if row, col is a valid cell
        """
        return self._cols < col and self._rows < row

    @property
    def cell_count(self):
        """ get cells count (same as len(self))
        """
        return self._cols * self._rows

class BaseControl(Region):
    """ Base class for all UI controls
    """
    DRAG_MODE_BODY = 999

    def __init__(self, x, y, width=8, height=8, color=None, conf=None, *args, **kwargs):
        super().__init__(x, y, width, height, *args, **kwargs)                
        self._app = None
        self._conf = conf
        self._name = None
        self._verbose = True
        self._color = COLOR_FOREGROUND if color is None else color
        self._visible = True
        self._selected = False                               
        self._drop_shadow = True
        self._selectable = False
        self._dirty = True # sometimes used        
        self._on_click_cb = None
        self._on_doubleclick_cb = None
        self._on_drag_move_cb = None
        self._on_keypress_cb = None
    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        if not isinstance(value, bool):
            raise ValueError("selected value must be boolean")
        self._selected = value

    @property
    def drop_shadow(self):
        return self._drop_shadow
    
    @drop_shadow.setter
    def drop_shadow(self, drop):
        self._drop_shadow = bool(drop)

    @property
    def name(self):
        """ a control is assigned a name if it's referenced by an application object
            field, i.e. app.control1 else is None
            note: helpful for auto-saving control values in a conf file
        """
        return self._name

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        if isinstance(color, pygame.Color):
            color = (color.r, color.g, color.b)
        self._color = color

    @property
    def app(self):
        """ reference to application object
        """
        return self._app

    def on_drag_move(self, f_cb):
        self._on_drag_move_cb = types.MethodType(f_cb, self)
    on_drag_move = property(fset=on_drag_move)        

    def on_click(self, f_cb):
        """ property to assign on click callback """
        self._on_click_cb = types.MethodType(f_cb, self)
    on_click = property(fset=on_click)
    
    def on_doubleclick(self, f_cb):
        """ property to assign on doubleclick callback """
        self._on_doubleclick_cb = types.MethodType(f_cb, self)
    on_doubleclick = property(fset=on_doubleclick)

    def on_keypress(self, f_cb):
        """ property to assign on doubleclick callback """
        self._on_keypress_cb = types.MethodType(f_cb, self)
    on_keypress = property(fset=on_keypress)    

    def click_test(self, click_x, click_y):
        """ default method to see if a control is clicked """
        return self.pick_box(self.x, self.y, self.right, self.bottom, click_x, click_y)

    def drag_test(self, click_x, click_y):
        """ default method to see if a control is dragged via mouse """        
        if self.pick_box(self.x, self.y, self.right, self.bottom, click_x, click_y):            
            res = self.DRAG_MODE_BODY
            return res
        return None

    def drag_move(self, mode, x, y, x_rel, y_rel, app, button):
        if self._on_drag_move_cb is not None:
            self._on_drag_move_cb(mode, x, y, x_rel, y_rel, app, button)

    def key_pressed(self, key, app):
        if self._on_keypress_cb is not None:
            self._on_keypress_cb( key, app)

    def clicked(self, click_x, click_y, button, app):
        """ is called if a control is clicked
            override it to create your own click handler
        """ 
        if self._on_click_cb is not None:
            return self._on_click_cb(click_x, click_y, button, app)
        return True

    def doubleclicked(self, click_x, click_y, button, app):
        if callable(self._on_doubleclick_cb):
            return self._on_doubleclick_cb(click_x, click_y, button, app)
        return True
    
    @staticmethod
    def pick_box(x1, y1, x2, y2, x, y):
        """ test if box defined by x1, y1, x2, y2 can be
            clicked at x, y (commonly mouse position)
        """
        return x>=x1 and y>=y1 and x<=x2 and y<=y2

    @staticmethod
    def pick_circle(c_x, c_y, radius, x, y):
        """ test if circle defined by c_x, c_y, and radius can be
            clicked at x, y (commonly mouse position)
        """
        return (x-c_x)**2 + (y-c_y)**2 <= radius**2
    @staticmethod
    def pick_point(px, py, x, y, size=2):
        """ test if a vertex define by px, py, and size
            can be clicked or dragged at x, y (commonly mouse position)
        """
        return abs(x-px)<=size and abs(y-py)<=size

    def  __repr__(self):
        return "<{.__class__.__name__}@{:x}>".format(self, id(self))

    def __str__(self):
        return "<{0.__class__.__name__}{1}:x={0.x:d},y={0.y:d}>".format(self, "" if self.name is None else "'"+self.name+"'")

class Layout(Region):
    def __init__(self, x=None, y=None, spacing=None, *args, **kwargs):
        super().__init__(x, y, 0, 0, *args, **kwargs)
        self._items = []
        self._index = 0  
        self._spacing = spacing

    @Region.height.setter
    def height(self, val):
        self._height = val
        if self.layout is not None:
            self.layout._re_align()

    @Region.width.setter
    def width(self, val):
        self._width = val
        if self.layout is not None:
            self.layout._re_align()        

    def add(self, val):
        if not isinstance(val, (BaseControl, Layout)):
            raise ValueError("You can only store controls and layouts here")
        if val in self._items:
            raise ValueError("The item is already in the layout")
        if val.layout and val.layout is not self:
            val.layout.remove(val)
        if self._y is None:
            self._y = val.y
        if self._x is None:
            self._x = val.x
        self._items.append(val)        
        val.layout = self
        return val

    def remove(self, val):
        self._items.remove(val)        
        val.layout = None
        return val

    @property
    def spacing(self):
        return self._spacing

    @Region.y.setter
    def y(self, val):
        for item in self._items:
            if item.y is not None:
                item.y += (val-self._y)
        self._y = val
    
    @Region.x.setter
    def x(self, val):
        for item in self._items:
            if item.x is not None:
                item.x += (val-self._x)
        self._x = val

    def _re_align(self):
        pass            
    
    def __iter__(self):
        self._iter = self._make_iter()
        return self    

    def _make_iter(self):         
        for item in self._items:
            if isinstance(item, BaseControl):
                if hasattr(item, "_controls"):
                    yield item
                    if item._visible:                       
                        for ctrl in item._controls:                        
                            yield ctrl
                    else:
                        continue                            
                else:
                    yield item
            else:
                for val in item:
                    yield val        

    def __next__(self):
        return next(self._iter)

class SpriteSheet(BaseGrid):
    """ generic sprite sheet
    """
    _sprite_imgs = {}
    def __init__(self, image_fn, sprite_size, cols=None, rows=None, colorkey=None, scale=None, sprite_info_fn=None, darker=None):
        
        self._image_basename = os.path.basename(image_fn)
        self._image_fn = image_fn
        if not self._image_fn in self.__class__._sprite_imgs:
            print("Loading:", image_fn)
            img = pygame.image.load( image_fn )
            img = img.convert()
            self.__class__._sprite_imgs[self._image_fn] = img
        else:
            img = self.__class__._sprite_imgs[self._image_fn]

        self._darker = darker

        self._sprite_info_fn = sprite_info_fn

        if cols is None:
            im_size_w, im_size_h = img.get_size()
            cols = im_size_w//sprite_size[0]
            rows = im_size_h // sprite_size[1]

        super().__init__(cols, rows)

        self._colorkey = colorkey        
        self._image = img
        self._sprites = []        
        self._sprite_size = sprite_size
        self._scale = scale
        self._rebuild_sprites()

    @property
    def image(self):
        return self._image

    def _rebuild_sprites(self):
        if self._colorkey is None:
            self._image.set_colorkey(self._image.get_at((0,0)))

        sprite_w, sprite_h = self._sprite_size

        if self._darker is not None:
            darken = pygame.Surface(self._image.get_size()).convert()
            darken.fill((self._darker, self._darker, self._darker))
            self._image = self._image.copy()
            self._image.blit(darken, (0,0), special_flags=pygame.BLEND_RGB_SUB)            

        if self._scale is not None:
            size = self._image.get_size()
            sprite_w = int(sprite_w * self._scale)
            sprite_h = int(sprite_h * self._scale)
            self._image = pygame.transform.scale(self._image, ( int(size[0]*self._scale), int(size[1]*self._scale) ) )
        
        for row in range(self._rows):            
            for col in range(self._cols):
                self._sprites.append( self._image.subsurface((col*sprite_w, row*sprite_h, sprite_w, sprite_h)) )        

    def __getitem__(self, idx):
        #print(self, '__getitem__', idx, self._sprites)
        return self._sprites[idx]                 

    def render_sprites(self, surf, spriteids_list, x, y):
        cur_y = y
        sprite_w, sprite_h = self[0].get_size()
        for scanline in spriteids_list:
            cur_x = x
            for sprite_no in scanline:
                if sprite_no is not None:                    
                    surf.blit(self._sprites[sprite_no], (cur_x, cur_y))
                cur_x += sprite_w
            cur_y += sprite_h
        return (cur_x-x, cur_y-y) # size of the sprites area

class VerticalLayout(Layout):
    def __init__(self, x=None, y=None, spacing=2):
        super().__init__(x, y, spacing)

    def add(self, item):
        super().add(item)
        self._re_align() 
        return item

    def _re_align(self):
        self._height = 0
        for item in self._items:
            item.y = self.y + self._height
            self._height += item.height + self.spacing
            if isinstance(item, Layout):
                self._height += item.spacing
            if self.x is not None:
                item.x = self.x
            if self.width<item.width:
                self.width = item.width
        super()._re_align()            
            
class GridLayout(Layout, BaseGrid):
    """ arrange controls in a grid 
        param alignment: 0 - left aligned, 1 - items are centered in cells
    """
    def __init__(self, cols, rows, x=None, y=None, spacing=2, alignment=0):
        super().__init__(x, y, spacing, cols, rows)
        self._grid=[[0]*cols for _ in range(rows)]
        for row in range(rows):
            for col in range(cols):
                self._grid[row][col] = dict(width=0, height=0, item=None)
        self._alignment = alignment

    def add(self, item, cell_pos):
        col, row = cell_pos
        super().add(item)
        grid_cell = self._grid[row][col]
        grid_cell['item']=item
        self._re_align()         
        return item

    def _re_align(self):
        self._height = 0
        self._width = 0
        col_widths = [0] * self._cols
        
        for col in range(self._cols):            
            for row in range(self._rows):                
                cell = self._grid[row][col]
                item = cell["item"]
                if item is None:
                    continue
                if item.width > col_widths[col]:
                    col_widths[col] = item.width

        for row in range(self._rows):
            cell_height = 0
            #print('start of the loop, cell_height:', cell_height)
            item_left=0
            for col in range(self._cols):
                cell = self._grid[row][col]
                item = cell["item"]
                if item is None:
                    continue
                if self._alignment==0:
                    item.x = self.x + item_left
                else:
                    item.x = self.x + item_left + (col_widths[col] - item.width)//2
                item_left += col_widths[col] + self.spacing
                if isinstance(item, Layout):
                    item_left += item.spacing                    
                if cell_height < item.height:
                    cell_height = item.height
                    #print("bubble gum 2")
                item.y = self.y + self._height
            h_incr = cell_height + self.spacing
            #print('h_incr:', h_incr, "cell_height:", cell_height, "self.spacing:", self.spacing)     
            self._height += h_incr
            if self._width<item_left:
                self._width=item_left       
            if isinstance(item, Layout):
                self._height += item.spacing
        super()._re_align()

class Spacer(Layout):
    def __init__(self, spacing):
        super().__init__(None, None, spacing)

    def add(self, val):
        raise ValueError("Can't add items to spacer")
    @Region.y.setter
    def y(self, val):
        pass

    @Region.x.setter
    def x(self, val):
        pass

class HorizontalLayout(Layout):
    def __init__(self, x=None, y=None, spacing=0, *args, **kwargs):
        #print('HorizontalLayout __init__:', args, kwargs)
        super().__init__(x, y, spacing, *args, **kwargs)
        self._width = 0
        
    def add(self, item):
        super().add(item)
        self._re_align()
        return item           

    def _re_align(self):       
        super()._re_align() 
        self._width = 0
        for i, item in enumerate(self._items, start=1):
            if self.x is None:
                break
            item.x = self.x + self._width
            self._width += item.width + (self.spacing if i<len(self._items) else 0)
            if isinstance(item, Layout):
                self._width += item.spacing
            if self.y is not None:
                item.y = self.y
            if self.height<item.height:
                self.height = item.height
            
class GridCtrl(BaseControl, BaseGrid):
    """ Display pixel grid for sprite editing """
    DRAW_GRID_AT_ZOOM = 5
    MAX_ZOOM = 32
    def  __init__(self, size, color=COLOR_GRID, zoom=4, max_width=None, **kwargs):
        super().__init__(0, 0, 0, 0, color, cols=size[0], rows=size[1], **kwargs)
        
        if max_width is not None:
            for z in range(1,self.MAX_ZOOM+1):
                self._zoom = z
                if self.width>=max_width:
                    break
        else:
            self._zoom = zoom
        self._max_width = max_width
        self.size = size        
        self._onion_skin = None
        self._on_painted_cb = None

    def on_painted(self, f_cb):
        """ property to assign on painted callback """
        self._on_painted_cb = types.MethodType(f_cb, self)
    on_painted = property(fset=on_painted)

    @property
    def size(self):
        return self._size    

    @size.setter
    @makes_dirty
    @save_to_conf
    def size(self, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError('size val has to be list or tuple :P')
        self._size = value
        self._grid_image = pygame.Surface(self._size).convert()
        self._grid_image.fill( self._color )
        self._cols = self._size[0]
        self._rows = self._size[1]

    @makes_dirty
    def blit(self, surf, where=(0,0)):
        self._grid_image.blit(surf, where)

    @property
    def cell_width(self):
        return self._zoom
    @property
    def cell_height(self):
        return self._zoom

    @makes_dirty
    def set_onion_skin(self, surf):
        self._onion_skin = surf

    def cell_at_pos(self, x, y):
        """ get col, row and specified position x, y
        """
        cell_col = (x - self._x) // self.cell_width
        cell_row = (y - self._y) // self.cell_height
        if cell_col<0 or cell_row<0 or cell_col>(self._cols-1) or cell_row>(self._rows-1):
            return None
        return cell_col, cell_row
    
    def get_cellcolor_at_pos(self, x, y):
        res = self.cell_at_pos(x, y)
        if res is None:
            return None
        cell_col, cell_row = res
        return self._grid_image.get_at((cell_col, cell_row))        

    @makes_dirty
    def set_cellcolor_at_pos(self, x, y, value):
        res = self.cell_at_pos(x, y)
        if res is None:
            return None
        cell_col, cell_row = res
        self._grid_image.set_at( (cell_col, cell_row), value )

    @makes_dirty
    def line(self, x1, y1, x2, y2, color):
        p1 = self.cell_at_pos(x1, y1)
        p2 = self.cell_at_pos(x2, y2)
        if p1 is None or p2 is None:
            return None        
        pygame.draw.line(self._grid_image, color,p1, p2)

    @makes_dirty
    def set_grid_image(self, new_img):
        self.size = new_img.get_size()
        self._grid_image = new_img.copy()

    @property
    def grid_image(self):
        return self._grid_image

    @makes_dirty
    def flood_fill_at_pos(self, x,y,value):        
        res = self.cell_at_pos(x, y)
        if res is None:
            return None
        cell_col, cell_row = res
        flood_fill(self._grid_image, cell_col, cell_row, value)

    @property
    def image(self):
        if self._dirty:
            self._image = pygame.Surface((self.width, self.height)).convert()

            if self._onion_skin is not None:
                new_im = self._grid_image.copy()
                new_im.set_colorkey(self._grid_image.get_at((0,0)))

                im = pygame.transform.average_surfaces( [ new_im, new_im, self._onion_skin ])
                
                im.blit(new_im, (0,0), special_flags=0)
            else:
                im = self._grid_image

            pygame.transform.scale(im, (self.width, self.height), self._image)            
                        
            if self._zoom > self.DRAW_GRID_AT_ZOOM:
                grid_surf = pygame.Surface((self.width, self.height)).convert()        
                #grid_surf.fill(self.COLOR_WHITE)
                s = pygame.PixelArray(grid_surf)                        
                s[::self._zoom, 1::2] = (33,32,29)
                s[1::2, ::self._zoom] = (33,32,29)
                s.close()
                self._image.blit(grid_surf, (0,0),special_flags=pygame.BLEND_SUB)
                #self._image.blit(grid_surf, (0,0),special_flags=pygame.BLEND_MAX)

            pygame.draw.rect(self._image, COLOR_GRID_CELL, (0, 0, self.width, self.height), width=1)

            if self._on_painted_cb is not None:                
                self._on_painted_cb(self._grid_image, self.app)

            self._dirty = False
        return self._image        

    @Region.width.getter
    def width(self):
        return self._zoom * self._cols

    @Region.height.getter
    def height(self):
        return self._zoom * self._rows

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    @makes_dirty
    def zoom(self, zoom):
        if not isinstance(zoom, int):
            raise TypeError('zoom has to be int')
        if zoom<1 or zoom > 32:
            raise ValueError('zoom has to be > 1 and <= 32')
        self._zoom = zoom
    
    def draw(self, surf):
        surf.blit(self.image, (self._x, self._y))                

class ColorCell(BaseControl):
    def  __init__(self, width, height, color, *args, **kwargs):
        super().__init__(0, 0, width, height, *args, **kwargs)
        self._color = color
        self._border_color = COLOR_BORDER

    @BaseControl.color.getter
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        if isinstance(color, pygame.Color):
            color = (color.r, color.g, color.b)
        self._color = color

    def draw(self, surf):
        pygame.draw.rect(surf, self._color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(surf, self._border_color, (self.x, self.y, self.width, self.height), width=1)

class ROI(BaseControl):
    (DRAG_MODE_V1,
    DRAG_MODE_V2,
    DRAG_MODE_V3,
    DRAG_MODE_V4,
    DRAG_MODE_E1, 
    DRAG_MODE_E2, 
    DRAG_MODE_E3, 
    DRAG_MODE_E4) = range(1, 9)

    def  __init__(self, width, height, *args, **kwargs):
        super().__init__(0, 0, width, height, *args, **kwargs)
        self._drop_shadow = False
        self._controls = Layout(self.x, self.y)
        self._label = self._controls.add(Label(""))      
        self._label.x += 5
        self._label.y += 5
        self._label._visible = False

    def pick_edge_hor(self, x, y, length, thinkness, pick_x, pick_y):
        dx = pick_x - x
        dy = pick_y - y
        return dx >= 0 and dx <= length and abs(dy)<=thinkness

    def pick_edge_vert(self, x, y, length, thinkness, pick_x, pick_y):
        dx = pick_x - x
        dy = pick_y - y
        return dy>=0 and dy<=length and abs(dx)<=thinkness                

    def drag_test(self, x, y):
        if self.pick_point(self.x, self.y, x, y, size=3):
            return self.DRAG_MODE_V1
        elif self.pick_point(self.right, self.y, x, y, size=3):
            return self.DRAG_MODE_V2
        elif self.pick_point(self.right, self.bottom, x, y, size=3):
            return self.DRAG_MODE_V3          
        elif self.pick_point(self.x, self.bottom, x, y, size=3):
            return self.DRAG_MODE_V4
        elif self.pick_edge_hor(self.x, self.y, self.width, 3, x, y):
            return self.DRAG_MODE_E1
        elif self.pick_edge_hor(self.x, self.bottom, self.width, 3, x, y):
            return self.DRAG_MODE_E3
        elif self.pick_edge_vert(self.x, self.y, self.height, 3,  x, y):
            return self.DRAG_MODE_E4
        elif self.pick_edge_vert(self.right, self.y, self.height, 3,  x, y):
            return self.DRAG_MODE_E2     


    def drag_move(self, mode, x, y, x_rel, y_rel, app, button):
        super().drag_move(mode, x, y, x_rel, y_rel, app, button)
        if button==pygame.BUTTON_LEFT:
            if mode==self.DRAG_MODE_V1:            
                self.x = x
                self.y = y
                self.width-=x_rel
                self.height-=y_rel
            elif mode==self.DRAG_MODE_V2:
                self.width+=x_rel
                self.y = y
                self.height-=y_rel
            elif mode==self.DRAG_MODE_V3:
                self.width+=x_rel
                self.height+=y_rel
            elif mode==self.DRAG_MODE_V4:
                self.x = x
                self.width-=x_rel
                self.height+=y_rel
            elif mode in (self.DRAG_MODE_E1, self.DRAG_MODE_E2, self.DRAG_MODE_E3, self.DRAG_MODE_E4):
                self.x += x_rel
                self.y += y_rel
            
            if self.width<=0:
                self.x+=self.width
                self.width = 1
            if self.height<=0:
                self.y+=self.height
                self.height=1

    @property
    def roi(self):
        return (self.x, self.y, self.width, self.height)

    @Region.x.getter
    @load_from_conf
    def x(self):    
        return self._x

    @x.setter
    @makes_dirty
    @save_to_conf
    def x(self, val):        
        self._x = val
        self._controls.x = val          

    @Region.y.getter
    @load_from_conf 
    def y(self):
        return self._y        

    @y.setter
    @makes_dirty
    @save_to_conf
    def y(self, val):
        self._y = val
        self._controls.y = val   

    @Region.width.getter
    @load_from_conf
    def width(self):
        return self._width

    @width.setter
    @makes_dirty
    @save_to_conf
    def width(self, val):
        self._width = val
    
    @Region.height.getter
    @load_from_conf
    def height(self):
        return self._height       

    @height.setter
    @makes_dirty
    @save_to_conf
    def height(self, val):
        self._height = val  

    def set_text(self, s):
        self._label.text = s

    def _redraw(self):
        if self.name is not None and not self._label._visible:
            self._label.text = self.name
            self._label._visible = True
        self._surface =pygame.Surface((self.width,self.height)).convert()
        self._surface.set_colorkey(self._surface.get_at((0,0)))
        line_length =2
        h = self.height-1
        w = self.width-1
        for x in range(0, self.width, line_length+2):
            pygame.draw.line(self._surface, (245, 233, 246), (x, 0), (x+line_length, 0))
            pygame.draw.line(self._surface, (245, 233, 246), (x, h), (x+line_length, h))
        for y in range(0, self.height, line_length+2):
            pygame.draw.line(self._surface, (245, 233, 246), (0, y), (0, y+line_length))
            pygame.draw.line(self._surface, (245, 233, 246), (w, y), (w, y+line_length))

        self._dirty = False         
    
    def draw(self, surf):
        if self._dirty:
            self._redraw()
        surf.blit(self._surface, (self.x, self.y), special_flags=pygame.BLEND_ADD)
        pygame.draw.rect(surf, (245,234,255), (self.x-1, self.y-1, 4,4),width=1)
        pygame.draw.rect(surf, (245,234,255), (self.right-2, self.y-1, 4,4),width=1)
        pygame.draw.rect(surf, (245,234,255), (self.right-2, self.bottom-2, 4,4),width=1)
        pygame.draw.rect(surf, (245,234,255), (self.x-1, self.bottom-2, 4,4),width=1)

class ButtonCtrl(BaseControl):
    def  __init__(self, label, width, height, color=COLOR_FOREGROUND, font_color=COLOR_WHITE, btn_image=None, *args, **kwargs):
        super().__init__(0, 0, width, height, color, *args, **kwargs)
        self._label_txt = label
        self._controls = Layout(self.x, self.y)
        self._label_ctrl = self._controls.add( Label(self._label_txt, shaded=True, max_width=width-4, font_color=font_color) )
        self._label_ctrl.x = self.x + (width - self._label_ctrl.width)//2
        self._label_ctrl.y = self.y + (height - self._label_ctrl.height)//2
        self._drop_shadow=False
        self._shade_color = COLOR_FOREGROUND_DARK
        self._light_color = COLOR_FOREGROUND_LIGHT
        self._is_pushed = 0
        self._btn_image = btn_image
        self._is_highlighted = False
        self._pushed_cb = None
        self._panel_color = darker(self._color, 0.1)

    def on_pushed(self, f_cb):
        """ property to assign on painted callback """
        self._pushed_cb = types.MethodType(f_cb, self)
    on_pushed = property(fset=on_pushed)   

    def set_highlighted(self, highlighted):
        self._is_highlighted = highlighted

    @property
    def btn_image(self):
        return self._btn_image

    @btn_image.setter
    def btn_image(self, surf):
        self._btn_image = surf

    @BaseControl.x.setter
    def x(self, val):
        self._x = val
        self._controls.x  = self._x        

    @BaseControl.y.setter
    def y(self, val):
        self._y = val        
        self._controls.y  = self._y

    @property
    def is_pushed(self):
        return self._is_pushed

    def set_text(self, s):
        self._label_txt = s
        self._label_ctrl.text = self._label_txt
        self._label_ctrl.x = self.x + (self.width - self._label_ctrl.width)//2

    @is_pushed.setter
    def is_pushed(self, value):
        self._is_pushed = int(value)
        if self._is_pushed!=0:
            self._is_pushed=1
        self._label_ctrl.x = self.x + (self.width - self._label_ctrl.width)//2
        self._label_ctrl.y = (self.y + (self.height - self._label_ctrl.height)//2) + self._is_pushed

    def pushed(self):
        """ executes when the button is pushed 
        """
        if self._pushed_cb is not None:
            self._pushed_cb()        
            
    def draw(self, surf):        
        pygame.draw.rect(surf, self._panel_color, (self.x, self.y, self.width, self.height))
        draw_shaded_frame(surf, self._x, self._y, self.width, self.height, self._shade_color, self._light_color, mode=self._is_pushed)
        if self._btn_image is not None:
            img_size_x, img_size_y = self._btn_image.get_size()
            im_x = self._x + (self.width - img_size_x) // 2
            im_y = self._y + (self.height - img_size_y) // 2
            surf.blit(self._btn_image, (im_x, im_y + self._is_pushed ) )
        if self._is_highlighted:            
            highlight = pygame.Surface((self.width, self.height)).convert()
            highlight.fill((25, 23, 19))
            surf.blit(highlight, (self.x, self.y), special_flags=pygame.BLEND_ADD )

class Undoable():
    UNDO_SIZE = 5
    def  __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._undo_history = []        

    def _save_undo(self):
        self._undo_history.append(self._image.copy())
        if len(self._undo_history)>self.UNDO_SIZE:
            excess_i = len(self._undo_history)-self.UNDO_SIZE
            self._undo_history = self._undo_history[excess_i:]    

    def clears_undo(f):
        def wrapped(*args, **kwargs):        
            self = args[0]
            self.clear_undo()
            res = f(*args, **kwargs)
            return res
        return wrapped            

    def undoable_action(f):
        def wrapped(*args, **kwargs):        
            self = args[0]
            self._save_undo()
            res = f(*args, **kwargs)
            return res
        return wrapped    

    def clear_undo(self):
        self._undo_history = []

    def undo(self):
        try:
            undo = self._undo_history.pop()
            self._image = undo        
        except IndexError:
            print('Nothing to undo')    

class SliderCtrl(BaseControl):
    """ a regular slider """
    DRAG_MODE_SLIDER=1
    def  __init__(self, width=100, height=18, value_range=(0, 100), *args, **kwargs):
        super().__init__(0, 0, width, height, *args, **kwargs)
        self._on_pos_change_cb = None
        self._slider_pos = 0
        self._old_slider_pos = 0
        self.set_range(*value_range)

    def _slider_rect(self):
        return (self.x + 1 + self.pos, self.y + 1, 5, self.height - 2)

    def set_range(self, n1, n2):
        if n1>n2:
            raise ValueError('set_range has to be: n1 < n2')
        self._min = n1
        self._max = n2

    def drag_test(self, x, y):
        x1, y1, w1, h1 = self._slider_rect()
        x2 = x1 + w1
        y2 = y1 + h1
        if self.pick_box(x1, y1, x2, y2, x, y):
            return self.DRAG_MODE_SLIDER
        return None

    def on_pos_change(self, f_cb):
        self._on_pos_change_cb = types.MethodType(f_cb, self)
    on_pos_change = property(fset=on_pos_change)    

    def drag_move(self, mode, x, y, x_rel, y_rel, app, button):
        super().drag_move(mode, x, y, x_rel, y_rel, app, button)
        if button==pygame.BUTTON_LEFT:
            if mode==self.DRAG_MODE_SLIDER:
                self._old_slider_pos = self._slider_pos
                self.pos +=x_rel
                if self._slider_pos<0:
                    self.pos=0
                if self._slider_pos> (self.width - self._slider_rect()[2]):
                    self.pos= self.width  -  self._slider_rect()[2]
                if self._on_pos_change_cb is not None:
                    self._on_pos_change_cb(self._slider_pos, self._slider_pos-self._old_slider_pos,  app)

    @property
    @load_from_conf
    def pos(self):
        """ get slider relative position """
        return self._slider_pos

    @pos.setter
    @save_to_conf
    def pos(self, value):
        self._slider_pos = value

    @property
    def value(self):
        """ get control calculated value
            note that you should probably use this one in your program
         """  
        v_range = self._max - self._min        
        value = ((v_range * self.pos) / (self.width-self._slider_rect()[2])) + self._min
        return value
    
    def draw(self, surf):
        pygame.draw.rect(surf, self._color, (self.x, self.y, self.width, self.height))
        draw_shaded_frame(surf, self.x, self.y, self.width, self.height, darker(self.color, 0.3), brighter(self.color, 0.2))
        draw_shaded_frame(surf, self.x+3, self.y+2, self.width-6, 5, darker(self.color, 0.3), brighter(self.color, 0.2), mode=1)

        slider_rect = self._slider_rect()

        pygame.draw.rect(surf, self._color, slider_rect)
        draw_shaded_frame(surf, *slider_rect, darker(self.color, 0.3), brighter(self.color, 0.2))

class VerticalLine(BaseControl):
    def  __init__(self, length, thickness=3, color=COLOR_FOREGROUND, mode=0, *args, **kwargs):                        
        super().__init__(0, 0, thickness, length, color, *args, **kwargs)
        self._mode = mode
        self._shade_color = darker(self._color, SHADE_TINT)     
        self._light_color = brighter(self._color, LIGHT_TINT)

    @Region.height.setter
    def height(self, height):
        self._height = height

    def draw(self, surf):
        draw_panel(surf, self.x, self.y, self.width, self.height, self._color,  self._shade_color, self._light_color, self._mode )

class SpriteSheetCtrl(Undoable, BaseControl, BaseGrid):
    """ render a sprite sheet (for preview) """    
    def  __init__(self, sprite_size, cols, rows, *args, **kwargs):
        super().__init__(0, 0, 0, 0, COLOR_DEFAULT, cols=cols, rows=rows, *args, **kwargs)
        self._sprite_size = sprite_size        
        self._border_color = COLOR_BORDER
        self.select_region(0)
        self._zoom_factor = 1
        self._new_image()

    def get_size(self):
        return self._image.get_size()

    def _new_image(self, keep_contents=False):
        if keep_contents:
            old_image = self._image
        self._image = pygame.Surface((self.width, self.height))
        self._image = self._image.convert()
        self._image.fill(self._color)
        if keep_contents:
            self._image.blit(old_image, (0, 0))

    def select_region(self, col_or_idx, row=None):
        if row is None:            
            col = col_or_idx % self._cols
            row = col_or_idx // self._cols
        else:
            col = col_or_idx
        if col>=self._cols:
            raise ValueError('col should be < _columns')
        if row>=self._rows:
            raise ValueError('row should be > _rows')        
        self._region_col = col
        self._region_row = row

    @Undoable.clears_undo
    def add_col(self):
        self._cols = self._cols + 1
        self._new_image(True)

    @Undoable.clears_undo
    def add_row(self):
        self._rows = self._rows + 1
        self._new_image(True)                 
            
    @Undoable.clears_undo
    def set_image(self, image):
        size_x, size_y = image.get_size()
        sprite_size_x = 128
        sprite_size_y = 128
        while True:
            is_done = True
            if (size_x % sprite_size_x)!=0:
                sprite_size_x = sprite_size_x // 2
                sprite_size_y = sprite_size_x
                is_done = False
            if (size_y % sprite_size_y)!=0:
                sprite_size_y = sprite_size_y // 2
                sprite_size_x = sprite_size_y
                is_done = False
            if sprite_size_x<8 or sprite_size_y<8:               
                break            
            if is_done:
                break
        if sprite_size_x < 8:
            size_x = size_x + (size_x % sprite_size_x)
        if sprite_size_y < 8:
            size_y = size_y + (size_y % sprite_size_y)            

        self._sprite_size = (sprite_size_x, sprite_size_y)
        self._cols = size_x // self._sprite_size[0]
        self._rows = size_y // self._sprite_size[1]

        self._new_image()
        self._image.blit( image, (0, 0) )
        #print('image.get_size():', image.get_size(), 'size_x:', size_x, 'size_y:', size_y)        
        self.select_region(0)

    @property
    def region_x(self):
        return self._region_col * self._sprite_size[0]
    @property
    def region_y(self):
        return self._region_row * self._sprite_size[1]

    @Undoable.undoable_action
    def update_current_region(self, surf):
        self._image.blit(surf, (self.region_x, self.region_y))

    def get_region_image(self, idx=None):
        if idx is None:
            try:
                res = self._image.subsurface((self.region_x, self.region_y, *self._sprite_size))
            except ValueError as e:
                print('self.region_x:', self.region_x, 'self.region_y:', self.region_y, 'self._sprite_size:', self._sprite_size)
                raise e                
        else:
            col, row = self.index_to_cell(idx)
            region_x = col * self._sprite_size[0]
            region_y = row * self._sprite_size[1]
            try:
                res = self._image.subsurface((region_x, region_y, *self._sprite_size))
            except ValueError as e:
                print('surf_x:', surf_x, 'surf_y:', surf_y, 'self._sprite_size:', self._sprite_size)
                raise e
        return res 

    def set_sprite_size( self, sprite_size_x, sprite_size_y  ):
        #print('sprite_size:', sprite_size_x, sprite_size_y)
        imgsize_x, imgsize_y = self._image.get_size()
        #print('self._image.get_size():', imgsize_x, imgsize_y)
        if sprite_size_x>imgsize_x:
            raise ValueError('sprite_size_x should be <= imgsize_x')
        if sprite_size_y>imgsize_y:
            raise ValueError('sprite_size_y should be <= imgsize_y')
        if (imgsize_x%sprite_size_x) or (imgsize_y%sprite_size_y):
            raise ValueError('image size should be divisible by new sprite_size')
        self.select_region(0)
        self._sprite_size = (sprite_size_x, sprite_size_y)
        self._cols = imgsize_x // self._sprite_size[0]
        self._rows = imgsize_y // self._sprite_size[1]

    @Region.width.getter
    def width(self):
        return self._cols * self._sprite_size[0]

    @width.setter
    def width(self, value):
        return None

    @Region.height.getter
    def height(self):
        return self._rows * self._sprite_size[1]

    @height.setter
    def height(self, value):
        return None

    @property
    def image(self):
        return self._image
        
    def draw(self, surf):        
        surf.blit(self.image, (self.x, self.y))
        pygame.draw.rect(surf, brighter( self._color, 0.5 ), (self.x-1, self.y-1, self.width+1, self.height+1), width=1)
        pygame.draw.rect(surf, brighter( self._color, 0.3 ), (self.region_x + self.x-1, self.region_y+self.y-1, self._sprite_size[0]+2, self._sprite_size[1]+2), width=1)

class TextEntry(BaseControl):
    typable_chars = "abcdefghijkhklmnopqrstquwxyz1234567890+-!#$%^*()~:;?,. "
    shifted_chars = {"1":"!", "2":"@", "3":"#", "4":"$", "5":"%", "6":"^", 
                     "7":"&","8":"*", "9":"(", "0":")", "-":"_", "[":"{", 
                     "]":"}", ",":"<", ".":">", "/":"?", "`":"~"}
    def  __init__(self, width=120, color=COLOR_FOREGROUND, *args, **kwargs):
        self._border = 2
        self._controls = Layout()
        self._controls._set_parent(self)
        super().__init__(0, 0, width, 12, color,  *args, **kwargs)
        self._controls.x = self.x
        self._controls.y = self.y
        self._lbl_text = self._controls.add( Label("hello, world", max_width=width, **kwargs) )
        self._lbl_text.x = self._border 
        self._lbl_text.y = self._border 
        self._height = self._lbl_text.height + self._border*2
        self._selectable = True
        self._editable = True
        self._drop_shadow = False

    def set_text(self, s):
        self._lbl_text.text = s
        
    def key_pressed(self, key, app):
        if key==pygame.K_BACKSPACE:
            self._lbl_text.text = self._lbl_text.text[0:len(self._lbl_text.text)-1]

        key_s = chr(key & 0xFF)        
        if pygame.key.get_mods() & pygame.KMOD_LSHIFT:
            shifted = True
        else:
            shifted = False

        if shifted:
            if key_s in self.shifted_chars:
                key_s = self.shifted_chars[key_s]
        
        if key_s in self.typable_chars:
            self._lbl_text.text = self._lbl_text.text + key_s

    

    def draw(self, surf):
        draw_panel(surf, self._x, self._y, self.width, self.height, self._color, mode=3)
        if self._selected and (pygame.time.get_ticks()//350)%2:
            cursor_pos_x = min(self._lbl_text.right+1, self.right-self._border)
            pygame.draw.rect(surf, self._color, (cursor_pos_x, self.y+self._border , 2,  self._lbl_text.height) )

    @Region.y.getter
    def y(self):
        return self._y

    @y.setter
    def y(self, val):
        self._y = val
        self._controls.y = val

    @Region.x.getter
    def x(self):
        return self._x

    @x.setter
    def x(self, val):
        self._x = val        
        self._controls.x = val

class SpritePreview(BaseControl):
    (
    TILE_MODE_NONE, 
    TILE_MODE_VERTICAL, 
    TILE_MODE_HORIZONTAL, 
    TILE_MODE_BOTH
    ) = range(4)
    def __init__(self, sprite_surf, zoom=2, color=COLOR_DEFAULT, *args, **kwargs):
        super().__init__(0, 0, 0, 0, color, *args, **kwargs)
        self._zoom = zoom        
        self._border = 1
        self.set_sprite( sprite_surf )
        self.set_tile_mode( self.TILE_MODE_NONE )
        self._preview_slides = 2
                
    def set_tile_mode(self, tile_mode):
        s_w, s_h = self._sprite.get_size()
        preview_w = s_w * self._zoom
        preview_h = s_h * self._zoom        
        margin = self._border * 2        
        self._tile_mode = tile_mode
        if self._tile_mode is self.TILE_MODE_NONE:
            self._image = pygame.Surface((preview_w+margin, preview_h+margin))
        elif self._tile_mode is self.TILE_MODE_HORIZONTAL:
            self._image = pygame.Surface((margin + preview_w*self._preview_slides, preview_h+margin))
        elif self._tile_mode is self.TILE_MODE_VERTICAL:
            self._image = pygame.Surface((margin + preview_w, preview_h*self._preview_slides+margin))
        elif self._tile_mode is self.TILE_MODE_BOTH:
            self._image = pygame.Surface((margin + preview_w*self._preview_slides, preview_h*self._preview_slides+margin))

        self._image = self._image.convert()
        self._width = int(self._image.get_size()[0])
        self._height = int(self._image.get_size()[1])                        

    def set_sprite(self, surf):
        self._sprite = surf

    def drag_move(self, mode, x, y, x_rel, y_rel, app, button):
        super().drag_move(mode, x, y, x_rel, y_rel, app, button)        
        if mode is self.DRAG_MODE_BODY:
            self.x += x_rel
            self.y += y_rel

    @property
    def image(self):
        s_w, s_h = self._sprite.get_size()
        preview_w = s_w * self._zoom
        preview_h = s_h * self._zoom
        sprite_preview = pygame.transform.scale( self._sprite, (preview_w, preview_h) )
        margin = self._border * 2

        if self._tile_mode is self.TILE_MODE_NONE:                         
            self._image.blit(sprite_preview, (self._border, self._border))
        elif self._tile_mode is self.TILE_MODE_HORIZONTAL:                                  
            for i in range(self._preview_slides):
                self._image.blit(sprite_preview, (self._border + i*preview_w, self._border)) 
        elif self._tile_mode is self.TILE_MODE_VERTICAL:
            for j in range(self._preview_slides):
                self._image.blit(sprite_preview, (self._border, self._border + j*preview_h))
        elif self._tile_mode is self.TILE_MODE_BOTH:
            for j in range(self._preview_slides):
                for i in range(self._preview_slides):
                    self._image.blit(sprite_preview, (self._border + i*preview_w, self._border + j*preview_h))            
                      
        im_w, im_h = self._image.get_size()

        draw_panel(self._image, 0, 0, im_w-1, im_h-1, self._color, mode=1, no_middle=True)
        
        return self._image

    def draw(self, surf):
        surf.blit(self.image, (self.x, self.y))

class FileDialog(BaseControl):
    RESULT_OK, RESULT_CANCELLED = range(1,3)
    def __init__(self, dir_, title, width=600, height=250, filter_ext=(".png",), *args, **kwargs):
        super().__init__(0, 0, width, height, *args, **kwargs)
        
        self._dir = dir_
        self._filter_ext = filter_ext
                
        self._controls = Layout(self.x, self.y)
        self._controls._set_parent(self)
        self._title_ctrl = self._controls.add(Label(title, shaded=True, max_width=self.width-10))
        self._title_ctrl.x = self.y + (self.width-self._title_ctrl.width)//2
        self._title_ctrl.y = self.y + 5

        self._file_grid = self._controls.add(GridLayout(3, 15))
        self._file_grid.x = self.x + 5
        self._file_grid.y = self.y + 50        

        self._btns_grid = self._controls.add(GridLayout(3, 1))
        self._btns_grid.y = self.y + self.height - 30          
        self._btns_grid.x = self.x + self.width - 210

        self.dir_path = self._controls.add( TextEntry(width=width-30) )
        self.dir_path.x = self.x + 30//2
        self.dir_path.y = self._title_ctrl.y + 25
        self.dir_path.set_text( os.path.abspath(dir_) )
        
        self._ok_btn = self._btns_grid.add( ButtonCtrl("Okay", 60, 25), (0,0) )
        self._ok_btn.on_click=self._ok_clicked
        self._btns_grid.add(Spacer(45), (1,0))
        self._cancel_btn = self._btns_grid.add( ButtonCtrl("Cancel", 80, 25), (2, 0) )
        self._cancel_btn.on_click=self._cancel_clicked
        self._visible = False
        self._selected_label = None
        self._on_result_cb = None
        self._result = None

    def clicked(self, click_x, click_y, button, app):
        for label in self._file_grid:
            if label.click_test(click_x, click_y):
                self._selected_label = label
                break
        super().clicked(click_x, click_y, button, app)

    def _ok_clicked(self, control, x, y, button, app):
        if button==pygame.BUTTON_LEFT:
            if self._on_result_cb is not None:
                self._visible=False
                self._on_result_cb(app, self._selected_label.text if self._selected_label is not None else None)

    def _cancel_clicked(self, control, x, y, button, app):
        if button==pygame.BUTTON_LEFT:
            if self._on_result_cb is not None:
                self._visible=False
                self._on_result_cb(app, None)

    def show(self):
        self._read_dir()
        self._visible = True

    def on_result(self, f_cb):
        self._on_result_cb = types.MethodType(f_cb, self)
    on_result = property(fset=on_result)        

    def _read_dir(self):
        self._files = os.listdir(os.path.dirname(__file__))        
        self._files = [fn for fn in self._files if os.path.splitext(fn)[1] in self._filter_ext]

        #print('self._files:', self._files)

        colums = self._file_grid.cols   
        rows = self._file_grid.rows
        col=0
        row=0
        files = [".."] + self._files    

        #print('len(self._file_grid):', len(self._file_grid))

        for i in range(self._file_grid.cell_count):      
            if i >= (len(files)):
                break
            fn = files[i]
            if (row+1) > (rows):
                row = 0
                col += 1
            try:
                self._file_grid.add( Label(fn, max_width=(self.width-12)//colums, font_color=COLOR_FILE_VIEWER_FONT), (col, row) ) 
                #print('adding:', fn)
            except IndexError as e:
                print("rows:", rows, "col:", col, "row:", row, "cells:",len(self._file_grid))
                raise e
            row += 1

    @Region.x.setter
    def x(self, value):
        self._x = value
        self._controls.x=self._x
        
    @Region.y.setter
    def y(self, value):
        self._y = value
        self._controls.y=self._y        

    def draw(self, surf):        
        draw_panel(surf, self.x, self.y, self.width, self.height, self.color, darker(self.color, 0.3), brighter(self.color, 0.2))
        
        draw_shaded_frame(surf, self.x+1, self.y+1, self.width-2, self._title_ctrl.height+8, darker(self.color, 0.3), brighter(self.color, 0.2), mode=1)
        pygame.draw.rect(surf, darker(self._color, 0.4), (self.x+5, self.y+3, self.width-10, self._title_ctrl.height+7-2), border_radius=4)

        file_viewer_rect = (self.x+3, self.y+45, self.width-5, self.height-(50+28+2+2))
        pygame.draw.rect(surf, COLOR_FILE_VIEWER, file_viewer_rect)
        draw_shaded_frame(surf, *file_viewer_rect, darker(self.color, 0.2), brighter(self.color, 0.3), mode=1)

        if self._selected_label is not None:
            label_size = (self._selected_label.width+2, self._selected_label.height+2)
            selection_rect = pygame.Surface(label_size).convert()
            selection_rect.fill(COLOR_FILE_SELECTION)
            surf.blit(selection_rect, (self._selected_label.x-1, self._selected_label.y-1), special_flags=pygame.BLEND_RGB_SUB )

class YesNoDialog(BaseControl):
    RESULT_YES, RESULT_NO, RESULT_IDK = range(1,4)
    HAS_IDK = 1
    def __init__(self, title, message, width=400, height=150, flags=0, *args, **kwargs):
        super().__init__(0, 0, width, height, *args, **kwargs)
        self._title = title
        self._message = message
        self._on_result_cb = None
        self._visible = False
        self._text_margin = 50
        self._controls = Layout(self.x, self.y)
        self._controls._set_parent(self)
        self._title_ctrl = self._controls.add(Label(self._title, shaded=True, max_width=self.width-10))
        self._title_ctrl.x = self.y + (self.width-self._title_ctrl.width)//2
        self._title_ctrl.y = self.y + 5        
        self._btns_grid = self._controls.add(GridLayout(5, 1))
        self._btns_grid.y = self.y + self.height - 30          
        self._btns_grid.x = self.x + 45

        self._yes_btn = self._btns_grid.add( ButtonCtrl("Yes", 60, 25), (0,0) )
        self._yes_btn.on_click=self._btn_clicked
        self._btns_grid.add(Spacer(45), (1,0))
        self._no_btn = self._btns_grid.add( ButtonCtrl("No", 80, 25), (2, 0) )
        self._no_btn.on_click=self._btn_clicked
        self._btns_grid.add(Spacer(45), (3,0))
        self._flags = flags
        self._result = None
        if self._flags & self.HAS_IDK:
            self._idk_btn = self._btns_grid.add( ButtonCtrl("idk", 80, 25), (4, 0) )      
            self._idk_btn.on_click=self._btn_clicked

        self._text_layout = self._controls.add(VerticalLayout())
        self._text_layout.y = 35
        self._text_layout.x = self._text_margin
        
        self._text_color = brighter((15, 22, 33), 0.7)        
        self._render_memo()

    def _btn_clicked(self, ctrl, x, y, mouse_button, app):
        if ctrl is self._yes_btn:
            self._result = RESULT_YES
        elif ctrl is self._no_btn:
            self._result = RESULT_NO
        elif ctrl is self._idk_btn:
            self._result = RESULT_IDK
        if mouse_button==pygame.BUTTON_LEFT:
            self._visible=False
            if self._on_result_cb is not None:                
                self._on_result_cb(app, self._selected_label.text if self._selected_label is not None else None)        

    def _render_memo(self):
        text_color = self._text_color
        max_width = self.width-self._text_margin*3
        for paragraph in self._message.split('\n'):
            memo_t = paragraph.split()
            words = []
            while len(memo_t):
                words.append(memo_t.pop(0))
                s = " ".join(words).encode('cp1251')
                if self._title_ctrl._rendered_text_width( s )>=max_width or len(memo_t)<=0:
                    if s:
                        self._text_layout.add(Label(s, font_color=text_color))                
                    words = []
            self._text_layout.add(Label("", font_color=text_color))

    def show(self):
        self._visible = True

    def on_result(self, f_cb):
        self._on_result_cb = types.MethodType(f_cb, self)
    on_result = property(fset=on_result)         

    def draw(self, surf):        
        draw_panel(surf, self.x, self.y, self.width, self.height, self.color, darker(self.color, 0.3), brighter(self.color, 0.2))
        draw_shaded_frame(surf, self.x+1, self.y+1, self.width-2, self._title_ctrl.height+8, darker(self.color, 0.3), brighter(self.color, 0.2), mode=1)
        pygame.draw.rect(surf, darker(self._color, 0.4), (self.x+5, self.y+3, self.width-10, self._title_ctrl.height+7-2), border_radius=4)        

    @Region.y.setter
    def y(self, value):
        self._controls.y=value
        self._y = value
    @Region.x.setter
    def x(self, value):
        self._controls.x=value
        self._x = value        

class ToolPanel(BaseControl):
    def  __init__(self, spacing=0, margin=2, color=COLOR_FOREGROUND, mode=0, *args, **kwargs):
        self._margin = margin
        self._controls = HorizontalLayout(spacing=spacing)
        self._controls._set_parent(self)
        self._line = self._controls.add(VerticalLine(24, 6, mode=3))
        self._line.on_drag_move = self._drag_line
        super().__init__(0, 0, self._controls.spacing+self._margin, self._margin, color, **kwargs)            
    
    def _drag_line(self, sender, mode, x, y, x_rel, y_rel, app, button):
        if mode==self.DRAG_MODE_BODY and button==pygame.BUTTON_LEFT:
            self.x+=x_rel
            self.y+=y_rel

    def add_item(self, value):
        return self._controls.add( value )

    def remove_item(self, value):
        return self._controls.remove( value )

    @Region.y.getter
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value
        self._controls.y = value + self._margin

    @Region.x.getter
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value
        self._controls.x = value + self._margin

    @Region.height.getter
    def height(self):
        return self._controls.height + self._margin * 2

    @Region.width.getter
    def width(self):
        return self._controls.width + self._margin * 2
    
    def draw(self, surf):
        draw_panel(surf, self._x, self._y, self.width, self.height, self._color )         

class StatusBar(BaseControl):
    def  __init__(self, height=24, margin=5, spacing=0, color=COLOR_FOREGROUND, mode=0, *args, **kwargs):        
        self._controls = HorizontalLayout(spacing=spacing)
        self._controls._set_parent = self              
        self._margin = margin
        super().__init__(0, 0, 8, height, color, **kwargs)
        self._drop_shadow = False
        self._cell_spacing_left = self._cell_spacing_right = 4
        self._cell_spacing_top = self._cell_spacing_bottom = 2

    def add_item(self, item):
        if not isinstance(item, Spacer):
            if len(self._controls._items):
                self._controls.add( Spacer(self._margin*2 + self._cell_spacing_left + self._cell_spacing_right) )
            else:
                self._controls.add( Spacer(self._margin + self._cell_spacing_left) )
        return self._controls.add( item )

    def remove_item(self, value):
        return self._controls.remove( value )

    @Region.y.getter
    def y(self):
        if self.app is not None:
            new_y = self.app.screen_height - self.height
            if new_y !=self._y:
                self._y = new_y
                self._controls.y = new_y + self._margin
                self._controls._re_align()
        return self._y

    @y.setter
    def y(self, value):
        self._y = value
        self._controls.y = value

    @Region.x.getter
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value
        self._controls.x = value

    @Region.height.getter
    def height(self):
        height =  self._controls.height+self._margin*2
        if height != self._height:
            self._height = height
            self._controls._re_align()
        return self._height

    @Region.width.getter
    def width(self):
        if self.app is not None:
            return self.app.screen_width
        return self._width

    def draw(self, surf):
        draw_panel(surf, self.x, self.y, self.width, self.height, self._color)
        line_sepa_width = 1
        for i, ctrl in enumerate(self._controls, start=1):
            
            draw_panel(surf, ctrl.x-self._cell_spacing_left, ctrl.y-self._cell_spacing_top, 
                        ctrl.width+self._cell_spacing_left+self._cell_spacing_right, ctrl.height+self._cell_spacing_top+self._cell_spacing_bottom, 
                        darker(self._color, 0.1), mode=1)
            # if i != 1:                
            #     draw_panel(surf, ctrl.x-self._cell_spacing_left-self._margin-line_sepa_width, ctrl.y-self._cell_spacing_top, 
            #                line_sepa_width, 
            #                ctrl.height+self._cell_spacing_top+self._cell_spacing_bottom, 
            #                 self._color, mode=1)        

class HorizontalLine(BaseControl):
    def  __init__(self, size, thickness=3, color=COLOR_FOREGROUND, mode=0, *args, **kwargs):
        super().__init__(0, 0, size, thickness, color, *args, **kwargs)
        self._thickness = thickness
        self._mode = mode

        self.SHADED_COLOR = darker(self._color, SHADE_TINT)
        self.LIGHTER_COLOR = brighter(self._color, LIGHT_TINT)            
        self._shade_color = self.LIGHTER_COLOR        
        self._light_color = self.SHADED_COLOR

    def draw(self, surf):
        draw_panel(surf, self.x, self.y, self.width, self.height, self._color,  self._shade_color, self._light_color, self._mode )

class Label(BaseControl):
    """ Basically draws a text string at specified coordinates
        Note: uses internal font sheet
    """
    extra_chars = r"_\/<>|][{}"
    def __init__(self, s, font_scale=1.0, font_color=(255, 255, 255), max_width=0, shaded=False, text_spacing=0, format_str=None, font_filename="basefont1_8.png", sprite_size=(8,8), *args, **kwargs):
        super().__init__(0, 0, 0, 0, font_color, *args, **kwargs)
        self._drop_shadow = False
        self._sheet = SpriteSheet("images/basefont1_8.png", sprite_size=(8,8))        
        self._value = None
        self._format_str = format_str
        self._font_scale = font_scale
        self._text_spacing = text_spacing
        self._font_filename = font_filename
        self._sprite_size = sprite_size
        self._s = s.lower()
        self._shaded = shaded        
        self._max_width = max_width

    @property
    def text(self):
        if self._format_str is not None and self._value is not None:
            res = self._format_str % self._value
            res = res.lower()
            return res
        return self._s

    @text.setter
    @makes_dirty
    def text(self, value):
        if not isinstance(value, str):
            raise TypeError('text value has to be a string')
        self._s = value.lower()

    @property
    def font_scale(self):
        return self._font_scale

    @font_scale.setter
    @makes_dirty
    def font_scale(self, scale):
        self._font_scale = scale

    @property
    def font_color(self):
        return self._color

    @font_color.setter
    @makes_dirty
    def font_color(self, color):
        self._color=color

    @property
    def max_width(self):
        return self._max_width        

    @Region.width.getter
    def width(self):
        #width = int(self._sprite_size[0] * len(self.text) * self._font_scale) + self._text_spacing*len(self.text)
        width = self._rendered_text_width(self.text)
        return width

    @Region.height.getter
    def height(self):
        height = int(self._sprite_size[1] * self._font_scale)
        return height

    @makes_dirty
    def set_format(self, format_str):
        self._format_str = format_str

    @property
    def value(self):
        return self._value

    @value.setter
    @makes_dirty
    def value(self, val):
        self._value = val

    def _unscaled_text_width(self, text):
        """ get not-scaled text width
        """        
        len_s = len(text)
        return self._sprite_size[0]*len_s + self._text_spacing*len_s

    def _rendered_text_width(self, s):
        """ get scaled text width
        """
        len_s = len(s)
        res = int(self._sprite_size[0] * len_s * self._font_scale) + self._text_spacing*len_s
        return res        

    def _render_string(self):        
        s = self.text
        if self._max_width>0 and (self._max_width < (self._rendered_text_width(s)+self._rendered_text_width("..")) ):
            last_index = (self._max_width // self._sprite_size[0]) - 2
            s = s[:last_index] + ".."

        label_img=pygame.Surface((max(1, self._unscaled_text_width(s)), self._sprite_size[1])).convert()
        label_img.set_colorkey( (0,0,0) )

        text_left = 0
        ord_z = ord('z')
        for i, c in enumerate(s):
            if isinstance(c, str):
                c_idx = ord(c)
                if (c_idx<13 or c_idx>ord_z) and not (c_idx>=192 and c_idx<=223) and not c in self.extra_chars:
                    c_idx = ord('?')                
            elif isinstance(c, int):
                c_idx = c
                if (c_idx<13 or c_idx>ord_z) and not (c_idx>=192 and c_idx<=223):
                    c_idx = ord('?')                
            else:
                raise TypeError('label text has to be string or byte')
            label_img.blit(self._sheet[c_idx], (text_left, 0))
            text_left += self._sprite_size[0] + self._text_spacing        

        if self._shaded:
            shaded_image = label_img.copy()
            colorImage = pygame.Surface(shaded_image.get_size()).convert_alpha()
            colorImage.fill(darker(self._color, 0.7))
            shaded_image.blit(colorImage, (0,0), special_flags = pygame.BLEND_RGBA_MULT)
            self._shaded_image = pygame.transform.scale(shaded_image, (self.width, self.height) )

        # text coloring
        colorImage = pygame.Surface(label_img.get_size()).convert_alpha()
        colorImage.fill(self._color)
        label_img.blit(colorImage, (0,0), special_flags = pygame.BLEND_RGBA_MULT)

        im_width = int(text_left*self._font_scale)
        if im_width<1:
            im_width = 1

        try:        
            self._image = pygame.transform.scale(label_img, (im_width, self.height))
        except Exception as e:
            raise e

    def draw(self, surface):
        if self._dirty:
            self._render_string()
            self._dirty = False
        if self._shaded:
            surface.blit(self._shaded_image, (self.x+1, self.y-1) )   
        surface.blit(self._image, (self.x, self.y) )
            
            