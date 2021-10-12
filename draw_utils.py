import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import math

import numpy as np
import pygame

_pi = math.pi
_pi_2 = math.pi * 2 


SHADE_TINT = 0.3
LIGHT_TINT = 0.2
FOREGROUND_DARK_TINT = 0.5

COLOR_BACKGROUND = (90, 87, 85)
COLOR_GRID = (120, 120, 120)
COLOR_GRID_CELL = (140, 140, 140)
COLOR_DEFAULT = (110, 100, 100)
COLOR_TRASPARENT = (110, 110, 120)
COLOR_BORDER = (230, 220, 230)
COLOR_FOREGROUND = (152, 168, 152)    
COLOR_FOREGROUND_LIGHT = (193, 214, 193)
COLOR_FOREGROUND_DARK = (113, 124, 113)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_FILE_SELECTION = (22, 12, 33)
COLOR_FILE_VIEWER = (215, 214, 212)
COLOR_FILE_VIEWER_FONT = (10, 10, 10)

get_ticks = pygame.time.get_ticks


def cuteoh(sprite_surf, chunk_size=6):
    subrects = []
    rect = sprite_surf.get_bounding_rect()
    h_subdivs = rect.width // chunk_size
    v_subdivs = rect.height // chunk_size
    cell_w = chunk_size
    cell_h = chunk_size
    for row in range(v_subdivs):
        for col in range(h_subdivs):
            x = col*cell_w
            y = row*cell_h
            ss = sprite_surf.subsurface((x, y, cell_w, cell_h))
            s_rect = ss.get_bounding_rect()            
            if not all(s_rect[2:]):
                continue
            subrects.append( (s_rect, (x, y), ss) )    
    return subrects

KERNEL_CACHE = {}

# Ghost at #pygame-community
def get_2d_blur_kernel(size, std_dev=0.1):
    size = int(size)
    if size not in KERNEL_CACHE:
        # mmm delicious math
        x_vals = [((i + 0.5) - size / 2) / (size / 2) for i in range(size)]
        KERNEL_CACHE[size] = numpy.array([1 / math.sqrt(2*math.pi*std_dev)*math.exp(-0.5*x**2/std_dev) for x in x_vals])
    return KERNEL_CACHE[size]

# Ghost at #pygame-community
def blur(array, kernel_size):
    kernel = get_2d_blur_kernel(kernel_size)
    # yoinked from https://stackoverflow.com/a/65804973
    array = numpy.apply_along_axis(lambda x: numpy.convolve(x, kernel, mode='same'), 0, array)
    array = numpy.apply_along_axis(lambda x: numpy.convolve(x, kernel, mode='same'), 1, array)
    return array


def get_casting_point(ln1, ln2):
    # the raycasting code by Emc2356
    # https://github.com/Emc2356/Visualizations/blob/main/RayCasting.py
    [x1, y1], [x2, y2] = ln1
    [x3, y3], [x4, y4] = ln2

    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if den == 0:  # line are parallel and they will never meet even if you stretch them out infinitely
        return

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    if t > 0 and t < 1 and u > 0:
        return pygame.math.Vector2(
            x1 + t * (x2 - x1),
            y1 + t * (y2 - y1)
        )
    else:
        return

#dist
#The first one is easy. If pos1 and pos2 are vectors, just subtract them

#angle
def measure_angle_vec(vec1, vec2):
    return (vec2 - vec1).as_polar()[0]



# def get_casting_point(self, wall):
#     x1 = wall.a.x
#     y1 = wall.a.y
#     x2 = wall.b.x
#     y2 = wall.b.y

#     x3 = self.pos.x
#     y3 = self.pos.y
#     x4 = self.pos.x + self.dir.x
#     y4 = self.pos.y + self.dir.y

#     den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
#     if den == 0:  # line are parallel and they will never meet even if you stretch them out infinitely
#         return

#     t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
#     u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
#     if t > 0 and t < 1 and u > 0:
#         return pygame.math.Vector2(
#             x1 + t * (x2 - x1),
#             y1 + t * (y2 - y1)
#         )
#     else:
#         return

# def intersect(line_1, line_2):
#     x3, y3, x4, y4 = self.pos.x, self.pos.y, self.pos.x + self.dir.x, self.pos.y + self.dir.y
#     x1, y1, x2, y2 = wall.a.x, wall.a.y, wall.b.x, wall.b.y
#     if den == 0:  # line are parallel and they will never meet even if you stretch them out infinitely
#         continue
#     t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
#     u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den

#     # if you want for 2 line segements you need to do u > 0 and u < 1 the u > 0 is for infinitely long line
#     if t > 0 and t < 1 and u > 0:
#         intersect_point = pygame.math.Vector2(x1 + t * (x2 - x1), y1 + t * (y2 - y1))

def make_matrix(roll, pitch, heading, x0, y0, z0):
    a = math.radians(roll)
    b = math.radians(pitch)
    g = math.radians(heading)

    T = np.array([[ math.cos(b)*math.cos(g), (math.sin(a)*math.sin(b)*math.cos(g) + 
                math.cos(a)*math.sin(g)), (math.sin(a)*math.sin(g) - 
                math.cos(a)*math.sin(b)*math.cos(g)), x0],
                [-math.cos(b)*math.sin(g), (math.cos(a)*math.cos(g) - 
                math.sin(a)*math.sin(b)*math.sin(g)), (math.sin(a)*math.cos(g) + 
                math.cos(a)*math.sin(b)*math.sin(g)), y0],
                    [        math.sin(b), -math.sin(a)*math.cos(b), math.cos(a)*math.cos(b), z0],
                    [ 0, 0, 0, 1]])
    return T


def project25d(wx, wy, wz, win_width, win_height, fov=90.0, viewer_distance=0):
    """ Transforms this 3D point to 2D using a perspective projection. """    
    factor = fov / (viewer_distance + wz)
    
    x = wx * factor + win_width / 2
    y = wy * factor + win_height / 2
    
    return int(x), int(y)    

def project25dAlt(wx, wy, wz, win_width, win_height, worldScale = 1.0):
    """ Project 3d coords into 2d plane (screen)
    """    
    ## I used the idea and the algorythm at: 
    ##   http://www.inversereality.org/tutorials/graphics%20programming/3dprojection.html    
    if wz == 0:
        OneOverZ = 0
    else:
        OneOverZ = 1.0 / float(wz)    
    
    sx = (wx * worldScale * OneOverZ) + win_width / 2
    sy = (wy * worldScale * OneOverZ) + win_height / 2
    
    return int(sx), int(sy)    

def clip(val, n, m):
    return min(m, max(n, val))

def measure_angle(x, y):
    return 180 - math.degrees( math.arctan2(x, y) )

def measure_angle_xy(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    return 180 - math.degrees( math.atan2(x2 - x1, y2 - y1) )    

def rotate(vector_length, angle):
    new_x = vector_length * math.cos(math.radians(angle))
    new_y = vector_length * math.sin(math.radians(angle))
    return (new_x, new_y)

        # Angle = math.atan2(player.y-self.rect.y, player.x-self.rect.x)
        # Angle = (math.cos(Angle) * self.speed, math.sin(Angle) * self.speed)    

def pivot_rotation(surf, pivot_x, pivot_y, angle):
    """ rotate pygame surface surf along specified pivot
    """
    sprite_w, sprite_h = surf.get_size()
    centerx = 0
    centery = 0
    
    pivot_c_x = pivot_x - sprite_w // 2
    pivot_c_y = pivot_y - sprite_h // 2    

    new_center_x = centerx + pivot_c_x
    new_center_y = centery + pivot_c_y
    
    c_off_x, c_off_y = rotate(pivot_c_x, angle)
    
    new_center_x += c_off_x
    new_center_y += c_off_y
    
    muzzle = pygame.transform.rotate(surf, 180-angle)
    m_size = muzzle.get_size()
    new_x = new_center_x - m_size[0]//2 - pivot_c_x
    new_y = new_center_y - m_size[1]//2 - pivot_c_y

    return new_x, new_y, muzzle    

def darker(color, amount):
    if isinstance(amount, int):
        return tuple(clip((c-amount), 0, 255) for c in color)
    elif isinstance(amount, float):
        return tuple(clip(int(c - c*amount), 0, 255) for c in color)
    raise ValueError("amount should be int or float")

def brighter(color, amount):
    if isinstance(amount, int):
        return tuple(clip(c+amount,0,255) for c in color)
    elif isinstance(amount, float):
        return tuple(clip(int(c + c*amount),0,255) for c in color)
    raise ValueError("amount should be int or float")

def pulse(range_, freq, shift=0.0):
    secs = math.degrees(shift * _pi_2) + 90 - (((get_ticks()%1000)/2.77)*freq) % 360
    return (1 - math.sin( math.radians(secs) ) ) * range_/2

def draw_line2(surf, coord1, coord2, xoff=0, yoff=0):
    x1, y1 = coord1
    x2, y2 = coord2
    pygame.draw.line(surf, (244, 233, 254), (x1+xoff, y1+yoff), (x2+xoff, y2+yoff)) 
    pygame.draw.circle(surf, (244, 233, 254), (x1+xoff, y1+yoff), 2)

def blur(a):
    """ experimental, blurs an numpy array a """
    kernel = np.array([[1.0,2.0,1.0], [2.0,4.0,2.0], [1.0,2.0,1.0]])
    kernel = kernel / np.sum(kernel)
    arraylist = []
    for y in range(3):
        temparray = np.copy(a)
        temparray = np.roll(temparray, y - 1, axis=0)
        for x in range(3):
            temparray_X = np.copy(temparray)
            temparray_X = np.roll(temparray_X, x - 1, axis=1)*kernel[y,x]
            arraylist.append(temparray_X)
    arraylist = np.array(arraylist)
    arraylist_sum = np.sum(arraylist, axis=0)
    return arraylist_sum    

def draw_shaded_frame(surf, x, y, width, height, shade_color=None, light_color=None, mode=0):
    """ draw a shaded frame (no middle)
        used to draw many controls
    """
    if shade_color is None:
        shade_color = COLOR_FOREGROUND_DARK
    if light_color is None:
        light_color = COLOR_FOREGROUND_LIGHT
    right = width + x
    bottom = height + y
    if mode & 1: 
        shade_color, light_color = light_color, shade_color
    pygame.draw.line(surf, light_color, (x+1, y), (right, y))
    pygame.draw.line(surf, darker(light_color, 0.1), (right, y), (right, bottom-1))
    pygame.draw.line(surf, shade_color, (x, bottom), (right-1, bottom))
    pygame.draw.line(surf, darker(shade_color, 0.1), (x, y+1), (x, bottom))

    if mode & 1:
        pygame.draw.line(surf, brighter(light_color, 0.25), (x, y), (x, y))
        pygame.draw.line(surf, brighter(light_color, 0.3), (right, bottom), (right, bottom))        
    else:
        pygame.draw.line(surf, darker(light_color, 0.25), (x, y), (x, y))
        pygame.draw.line(surf, darker(light_color, 0.3), (right, bottom), (right, bottom))

def draw_panel(surf, x, y, width, height, color, shade_color=None, light_color=None, mode=0, no_middle=False):
    if shade_color is None:
        shade_color = darker(color, SHADE_TINT)
    if light_color is None:
        light_color = brighter(color, LIGHT_TINT)
    if mode & 2:
        color = darker(color, FOREGROUND_DARK_TINT)
    if not no_middle:
        pygame.draw.rect(surf, color, (x, y, width, height))    
    draw_shaded_frame(surf, x, y, width, height, shade_color, light_color, mode=mode)    

def flood_fill(surf, f_x, f_y, color):
    """ fill surface surf with specified color at f_x, f_y
    """
    pixels = pygame.PixelArray(surf)
    width, height = surf.get_size()

    test_color = pixels[f_x, f_y]

    color = pygame.Color(color)
    color = (color.r, color.g, color.b)
        
    stack = []        
    stack.append((f_x, f_y))
    
    while len(stack):            
        x, y = stack.pop()
            
        if x < 0 or y < 0 or x >= width or y >= height:
            continue

        c_color = pixels[x, y]
        if pygame.Color(c_color)[1:]==color:
            continue

        if test_color==c_color:            
            pixels[x, y] = color
        else:
            continue

        stack.append((x + 1, y))   # right
        stack.append((x - 1, y))  # left
        stack.append((x, y + 1))  # down
        stack.append((x, y - 1))  # up         

angle = 45
def test():
    
    v= pygame.Vector2(10,0)
    v.rotate_ip(angle)  
    #rotate(10,angle)

if __name__ == '__main__':
    #import timeit
    #print(timeit.timeit("test()", globals=globals(), number=100000))        
    # print(get_casting_point([[0, 0], [50, 50]], [[50, 0], [0, 50]]))

    # player_x = 40
    # player_y = 50
    # rect_x = 400
    # rect_y = 300
    # speed = 2

    # angle = math.atan2(player_y-rect_y, player_x-rect_x)
    
    # move_x, move_y = (math.cos(angle) * speed, math.sin(angle) * speed) 

    # print('angle:', angle, math.degrees(angle), move_x, move_y)

    # #Angle = (math.cos(Angle) * self.speed, math.sin(Angle) * self.speed)   
    angle = 45
    v= pygame.Vector2(10,0).rotate(angle)
    
    print( v )
    #print( type(v + (10, 10)))
    #print( rotate(10,angle) )

