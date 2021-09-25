import os
import types

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from timeit import default_timer as timer

import pygame

from ui_controls import *
from draw_utils import *


class App():
    """ Encapsulates ingame loop among of other things
    """
    (MODE_PLAY, MODE_EDIT) = range(1, 3)    
    DOUBLECLICK_DELAY = 250 # ms

    def __init__(self, title=None, screen_size=(640, 480), fps=60, dpi_aware=False, resizeable=False, vsync=True):
        self._screen_size=screen_size
        self._title = title
        self._fps = fps
        self._dpi_aware = dpi_aware
        self._bgcolor = COLOR_BACKGROUND
        self._mode = self.MODE_PLAY # not currently used
        self._resizeable = resizeable
        self._vsync = vsync

        self._is_running = True        
        self._hide_gui = False
        self._clear_screen = True

        self._on_draw_cb = None
        self._on_post_draw_cb = None
        self._on_event_cb = None
        self._on_pre_draw_cb = None
        self._post_init_cb = None
        self._on_quit_cb = None #return false to postpone quit

        self._controls = Layout() # controls that are directly attached to the application
        self._next_user_event = pygame.USEREVENT + 1
        self._events = {} # holds even states
        self._idle_ticks = 0 # used by some controls
        self._anim_timer = 0 # used to animate sprites
        self._last_mouse_click_pos = (0, 0)
        self._last_mouse_click_ticks = 0
        self._last_mouse_click_button = pygame.BUTTON_LEFT

        self._pushed_btn = None
        self._shadow_offset = 6
        self._draged_controls = []
        self._clicked_control = None
        self._selected_control = None

        self._unsettling_events = frozenset([ pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP ])
                
    def __setattr__(self, name, value):
        """ setting app attribe with a controlo causes it to be added to application
            Note that it will add that control to the default layout unless a control
            already has a layout
        """
        if not name.startswith("_") and isinstance(value, (BaseControl, Layout)):
            value._name = name
            if value.layout is None and not value.layout is self._controls:
                self._controls.add( value )
            value._app = self    
        super().__setattr__(name, value)

    @staticmethod
    def _set_dpi_aware():
        import sys
        if sys.platform == 'win32':
            from ctypes import windll
            windll.user32.SetProcessDPIAware(True)   

    def set_mode(self, mode):
        self._mode = mode

    @property
    def screen_size(self):
        return self._screen_size
    @property
    def screen_width(self):
        return self._screen_size[0]
    @property
    def screen_height(self):
        return self._screen_size[1]        
    
    def on_event(self, f_cb):
        self._on_event_cb = types.MethodType(f_cb, self)
    on_event = property(fset=on_event)

    def post_init(self, f_cb):
        self._post_init_cb = types.MethodType(f_cb, self)
    post_init = property(fset=post_init)    

    def on_pre_draw(self, f_cb):
        self._on_pre_draw_cb = types.MethodType(f_cb, self)
    on_pre_draw = property(fset=on_pre_draw) #write only

    def on_draw(self, f_cb):
        """ set on draw callback """
        self._on_draw_cb = types.MethodType(f_cb, self)
    on_draw = property(fset=on_draw) #write only

    def on_quit(self, f_cb):
        """ set on quit callback """
        self._on_quit_cb = types.MethodType(f_cb, self)
    on_quit = property(fset=on_quit)

    def new_event(self, millis=0, once=0):
        event_id = self._next_user_event
        self._next_user_event += 1
        event = dict(event_id=event_id, millis=millis, once=once)
        self._events[event_id] = event
        if millis > 0:
            pygame.time.set_timer(event_id, millis, once)            
        return event_id

    def resume_event(self, event_id, millis=None, once=None):
        if not event_id in self._events:
            raise ValueError('only user events can be disabled')
        event = self._events[event_id]
        if millis is not None and millis<=0:
            raise ValueError('millis have to be > 0')
        event['millis']=millis
        if once is not None:
            event['once'] = once
        pygame.time.set_timer(event_id, event['millis'], event['once'])

    def pause_event(self, event_id):
        """ pause user event timer from firing """
        if not event_id in self._events:
            raise ValueError('only user events can be paused')
        event = self._events[event_id]
        pygame.time.set_timer(event_id, 0)

    @property
    def anim_timer(self):
        return self._anim_timer

    @property
    def controls(self):
        return self._controls

    def _init_pygame(self):
        if self._dpi_aware:
            self._set_dpi_aware()
        pygame.init()
        flags = pygame.DOUBLEBUF
        if self._resizeable:
            flags = flags | pygame.RESIZABLE
        self._screen = pygame.display.set_mode(self._screen_size, flags, vsync=self._vsync)        
        if self._title is not None:
            pygame.display.set_caption(self._title)
        self._clock = pygame.time.Clock()
        self.get_ticks = pygame.time.get_ticks  

        self._EVENT_CAPTURE_FRAME = self.new_event()
        self.EVENT_ANIM_HEARTBEAT = self.new_event(25)
        self.EVENT_DOUBLECLICK = self.new_event()

        self._shadow_surface = pygame.Surface((self.screen_width, self.screen_height)).convert()
        self.metrics_fps = 0

    def _dispatch_events(self):
        """ default engine's event dispatched that would also call
            a cutsom event handler cb here
        """
        for event in pygame.event.get():            
            if event.type == pygame.QUIT:
                if self._on_quit_cb is None or self._on_quit_cb():     
                    self.quit()
                
            if event.type==self.EVENT_ANIM_HEARTBEAT:
                self._anim_timer += 1
                continue

            if event.type in self._unsettling_events:
                self._idle_ticks = 0

            if event.type==pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos

                is_doubleclick = (self._last_mouse_click_ticks > (self.get_ticks() - self.DOUBLECLICK_DELAY) and
                                  self._last_mouse_click_button==event.button and self._last_mouse_click_pos==mouse_pos)

                self._last_mouse_click_ticks = self.get_ticks()
                self._last_mouse_click_button = event.button
                self._last_mouse_click_pos = event.pos                                                  

                if is_doubleclick:
                    doubleclick_event = pygame.event.Event(self.EVENT_DOUBLECLICK, {"pos": mouse_pos, "button": event.button})                                        
                    pygame.event.post(doubleclick_event)                    
                self._selected_control_old = self._selected_control
                for ctr in [ctrl for ctrl in self._controls if ctrl._visible and not self._hide_gui]:
                    #if event.button
                    drag_mode = ctr.drag_test(*mouse_pos)
                    if drag_mode is not None:
                        self._draged_controls += [(ctr, event.button, drag_mode)]

                    if ctr.click_test(*mouse_pos):
                        if isinstance(ctr, ButtonCtrl):
                            if self._pushed_btn is None:
                                self._pushed_btn = ctr
                                ctr.is_pushed = True
                        else:
                            if is_doubleclick:
                                ctr.doubleclicked(*mouse_pos, event.button, self)   
                            ctr.clicked(*mouse_pos, event.button, self)   
                        self._clicked_control = ctr
                        if ctr._selectable:
                            self._selected_control = ctr
                        else:
                            self._selected_control = None

                if self._selected_control_old is not None and self._selected_control_old!=self._selected_control:
                    self._selected_control_old.selected = False
                if self._selected_control is not None:
                    self._selected_control.selected = True

            elif event.type==pygame.MOUSEBUTTONUP:
                if self._pushed_btn is not None:
                    self._pushed_btn.is_pushed=False
                    self._pushed_btn.clicked(*pygame.mouse.get_pos(), event.button, self)
                    self._pushed_btn=None
                self._draged_controls = []
                self._clicked_control = None

            elif event.type==pygame.MOUSEMOTION:                 
                for ctrl, button, drag_mode in self._draged_controls:
                    ctrl.drag_move(drag_mode, *event.pos, *event.rel, self, button)

            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    if self._selected_control is not None:
                        self._selected_control.selected = False
                        self._selected_control = None
                if self._selected_control is not None:
                    self._selected_control.key_pressed(event.key, self)

            if event.type == pygame.VIDEORESIZE:
                self._screen_size = (event.w , event.h)
                self._shadow_surface = pygame.Surface((self.screen_width, self.screen_height)).convert()                                   

            # if event.type==self._EVENT_CAPTURE_FRAME:
            #     pass

            if callable(self._on_event_cb):
                self._on_event_cb(event)

        self._idle_ticks += 1

    def run(self):
        """ main pygame loop 
        """
        self._init_pygame()

        if self._post_init_cb is not None:
            self._post_init_cb()        
        
        while self._is_running:
            when = timer()

            self._dispatch_events()

            if self._clear_screen:
                self._screen.fill(self._bgcolor)

            if self._on_pre_draw_cb is not None:
                self._on_pre_draw_cb()

            # display shadow
            shadow = self._shadow_surface
            shadow.fill((0,0,0))
            shadow_color = (25, 23, 19)            
            if not self._hide_gui:
                for control in [ctrl for ctrl in self._controls if ctrl._visible and ctrl._drop_shadow and isinstance(ctrl, BaseControl)]:    
                    sh_off = self._shadow_offset            
                    pygame.draw.rect(shadow, shadow_color, (control.right, control.y + sh_off, sh_off, control.height))
                    pygame.draw.rect(shadow, shadow_color, (control.x+sh_off, control.bottom, control.width, sh_off))
                self._screen.blit(shadow, (0, 0), special_flags=pygame.BLEND_SUB)
                for control in [ctrl for ctrl in self._controls if ctrl._visible]:
                    control.draw(self._screen)

            if callable(self._on_draw_cb):
                self._on_draw_cb()

            pygame.display.flip()
            took = timer() - when

            self._clock.tick(self._fps)            
            self.metrics_fps = 1.0 / took            

        print('exited')
        pygame.quit()

    def quit(self):
        self._is_running = False

    @property
    def screen(self):
        return self._screen

    def blit(self, surf, where=(0,0), *args, **kwargs):
        self.screen.blit(surf, where, *args, **kwargs)

    def capture_gif(self, duration_secs, fps=5, rect=None):
        self._gif_frame_delay = 1000 // int(fps)
        self._capture_ends = self.get_ticks() + duration_secs*1000
        if rect is None:
            self._gif_rect = self.screen.get_rect()
        else:
            self._gif_rect = rect

    def _capture_gif_frame(self):
        frame_no = getattr(self, '_frame_no', 1)
        cropped = pygame.Surface(self._gif_rect[2], self._gif_rect[3])
        cropped.blit(self.screen, (0, 0), self._gif_rect)
        img_filename = "image_%d.png" % frame_no
        app._frame_no = frame_no + 1
        pygame.image.save(cropped, os.path.join("anims", img_filename))
        
    def _savegif(filename, source_path="anims/image_*.png", frame_delay=75, loop=1):
        #https://stackoverflow.com/questions/753190/programmatically-generate-video-or-animated-gif-in-python
        # save series of images to gif 
        # by Kris
        #https://stackoverflow.com/questions/64971675/pil-adding-text-to-a-gif-frames-adds-noise-to-the-picture
        # disable dithering 
        # by fdermishin
        from PIL import Image
        img, *imgs=[Image.open(f).quantize(method=Image.MEDIANCUT) for f in sorted(glob.glob(source_path))]
        img.save(fp=filename, format='GIF', append_images=imgs,
                save_all=True, duration=frame_delay, loop=loop)