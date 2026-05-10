#%%
import sys, re
from re import Match
from typing import Any
import threading
import time
import random
import queue

import glyphes
from pygameMultiFontRenderer import MultiFontRenderer
import pygame

#%%
# ======================
# CONFIG
# ======================

DEBUG = False

IFACES = ['enp6s0', 'wlp5s0']
# IFACES = ['eth0', 'wlan0']
BUFFER_SIZE = 1000

GLYPHS = (
    # glyphes.languages["hiragana"] + 
    glyphes.languages["ascii"] + 
    glyphes.languages["katakana"] + 
    # glyphes.languages["korean"] +
    # glyphes.languages["hebrew"] +
    # glyphes.languages["ascii"] + 
    glyphes.languages["symbols"] +
    glyphes.languages["digits"] +
    glyphes.languages["ascii"]
)

#%%

MAX_FLOW_LENGTH = 30
# SCREEN_WIDTH = 350 # 800
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 350
FONT_SIZE = 18
GRID_SEP = 1

cell_width = FONT_SIZE + GRID_SEP  # 20
num_cols = SCREEN_WIDTH // cell_width  # division entière
offset = ((SCREEN_WIDTH - (num_cols * cell_width)) // 2)
x_positions = [offset + (i * cell_width) for i in range(num_cols)]
MAX_STREAMS = len(x_positions) * 3
num_rows = (SCREEN_HEIGHT + MAX_FLOW_LENGTH) // cell_width
y_positions = [(i-1) * cell_width for i in range(num_rows+MAX_FLOW_LENGTH)]
y_positions

#%%
def scale_value(x, source_range, target_range):
    x_min, x_max = source_range
    if x_min > x_max:
        x_max, x_min = source_range
    y_min, y_max = target_range
    if y_min > y_max:
        y_max, y_min = source_range

    # sécurité
    if x < x_min or x > x_max:
        raise ValueError(f"{x} hors des bornes {source_range}")

    return y_min + ((x - x_min) * (y_max - y_min)) / (x_max - x_min)

#%%

usage = {x: 0 for x in x_positions}

def get_column():
    weights = [1 / (1 + usage[x]) for x in x_positions]
    choice = random.choices(x_positions, weights=weights)[0]
    usage[choice] += 1
    return choice

#%%
# ======================
# DATA STRUCTURES
# ======================
match_expressions = {
    "TCP": re.compile(
        r'.*IP.*(?P<src>\d+\.\d+\.\d+\.\d+)\.(?P<sport>\d+) > (?P<dst>\d+\.\d+\.\d+\.\d+)\.(?P<dport>\d+):.*'
    ),
    "TCP6": re.compile(
        r'.*IP6.*(?P<src>\b[0-9a-fA-F:]*:[0-9a-fA-F:]+\b)\.(?P<sport>\d+) > (?P<dst>\b[0-9a-fA-F:]*:[0-9a-fA-F:]+\b)\.(?P<dport>\d+):.*'
    ),
    "ARP": re.compile(
        r'.*ARP.*(?P<src>\d+\.\d+\.\d+\.\d+).*(?P<dst>\d+\.\d+\.\d+\.\d+).*'
    ),
    "*": re.compile(
        r'.*'
    )
}

packet_queue = queue.Queue(maxsize=BUFFER_SIZE)
lock = threading.Lock()

#%%
class Dot:
    def __init__(self, key, x: int, y: int, glyph: str | None = None, speed: float | None = None, color: tuple[int, int, int] | None = None, intensity: int | None = None):
        self.surface: pygame.Surface = None
        self.key = key
        self.x = x
        self.y = y
        self.glyph = "0" if glyph is None else glyph
        self.speed = 1 if speed is None else speed
        self.color = (255, 255, 255) if color is None else color
        self.head_color = (255, 255, 255)
        self.render_color = self.head_color
        self.intensity = 255 if intensity is None else intensity
        self.fade_duration = 1.8
        self.fade_elapsed = 0.0
        self.switch_duration = 3.0
        self.switch_elapsed = 0.0

        self.render(color=self.head_color)

    def activate(self, glyph: str | None = None, speed: float | None = None, color: tuple[int, int, int] | None = None):
        self.glyph = self.glyph if glyph is None else glyph
        self.speed = self.speed if speed is None else speed
        self.color = self.color if color is None else color
        self.render_color = self.head_color if color is None else color
        self.intensity = 255
        self.fade_elapsed = 0.0

        self.render(color=self.head_color)

    def update(self, dt, glyph: str | None = None, speed: float | None = None, color: tuple[int, int, int] | None = None, intensity: int | None = None):
        self.switch_elapsed += dt
        self.fade_elapsed += dt
        self.glyph = self.glyph if glyph is None else glyph
        self.speed = self.speed if speed is None else speed
        self.color = self.color if color is None else color
        self.intensity = self.intensity if intensity is None else intensity
        progress = min(self.fade_elapsed / self.fade_duration, 1.0)
        self.intensity = int(255 * (1.0 - progress))

        if self.switch_elapsed >= random.uniform(self.switch_duration, self.switch_duration * self.speed):
            self.glyph = random.choice(GLYPHS)
            self.switch_elapsed = 0.0

        self.render()

    def render(self, color: tuple[int, int, int] | None = None):
        self.render_color = self.render_color if color is None else color
        _render_color = {0: self.render_color[0], 1: self.render_color[1], 2: self.render_color[2]}
        if self.render_color[0] > self.color[0]:
            _render_color[0] = max(0, (self.render_color[0] - (255 - self.intensity) )) # // (self.speed / 2)))
        if self.render_color[1] > self.color[1]:
            _render_color[1] = max(0, (self.render_color[1] - (255 - self.intensity) )) # // (self.speed / 2)))
        if self.render_color[2] > self.color[2]:
            _render_color[2] = max(0, (self.render_color[2] - (255 - self.intensity) )) # // (self.speed / 2)))
        self.render_color = (_render_color[0], _render_color[1], _render_color[2])
        _color = (*self.render_color, self.intensity)
        self.surface = renderer.render_char(self.glyph, _color).copy()
        _tint = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        _tint.fill(_color)
        self.surface.blit(_tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


#%%
class Flow:
    def __init__(self, key, x:int | None = None, speed:float | None = None, text:str | None = None, color: tuple[int, int, int] | None = None):
        self.key = key

        if len(key) == 9:
            src, dst, sport, dport, proto, length, x, text, speed = key
        elif len(key) == 6:
            src, dst, sport, dport, proto, length = key

        if color is None:
            if proto == "TCP":
                color = (0, 255, 0)
            elif proto == "TCP6":
                color = (0, 255, 128)
            elif proto == "ARP":
                color = (128, 255, 0)
            else:
                color = (128, 255, 128)

        self.raise_destroy_event = False
        self.length = length
        self.speed = scale_value(self.length // 2, (min(random.randint(50, 100), self.length // 2), max(self.length, 200)), (0.01, 1.5)) if speed is None else speed
        self.y_iter = iter(y_positions)
        self.y = next(self.y_iter)
        self.x = get_column() if x is None else x
        self.last_update = time.time()
        self.glyphs = [random.choice(GLYPHS) for _ in range(self.length)] if text is None else [*text]
        self.color = color
        self.spawn_time = time.time()
        self.switch_duration = self.speed
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.switch_duration:
            self.y = next(self.y_iter)
            last_glyph = self.glyphs.pop()
            self.glyphs.insert(0, last_glyph)
            self.elapsed = 0.0

        # if ((self.y >= max(y_positions)) | # si on est arrivé en bas de l'écran
        #    (len(self.glyphs)<=1)): # si il n'y a plus rien dans le message
        if (self.y >= max(y_positions)): # si on est arrivé en bas de l'écran
            self.raise_destroy_event = True

#%%

# ---------- Font ----------
# IMPORTANT : utiliser une police qui supporte hiragana
font_paths = [
    "./fonts/DejaVuSans.ttf",
    "./fonts/NotoSans-Regular.ttf",
    # "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.ttf",
    "./fonts/NotoSansCJK-Bold.ttc",
    "./fonts/NotoSansArabic-Regular.ttf",
    "./fonts/NotoSansHebrew-Regular.ttf",
]

# ---------- Init ----------
pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Matrix Rain Code")
# clock = pygame.time.Clock()
renderer = MultiFontRenderer(font_paths, size=FONT_SIZE)

#%%
flows: dict[Any, Flow] = {}
dots: dict[Any, Dot] = {}
for x in x_positions:
    for y in y_positions:
        key = (x, y)
        dots[key] = Dot(key, x, y, glyph="1", color=(0, 255, 0), intensity=0)

#%%
print(f"Generate and Cache Glyphs len({len(GLYPHS)})")
renderer.render_text(GLYPHS) # on charge en cache la totalité des glyphs avant de lancer le screen
print(f"Let's Go !{' '*50}")

#%%
# ======================
# FLOW AGGREGATION
# ======================
def aggregator():
    while True:
        try:
            new_key = packet_queue.get(timeout=1)

            with lock:
                # if len(flows)>0:
                #     for key in list(flows.keys()):
                #         if flows[key].raise_destroy_event:
                #             del flows[key]
                #             if DEBUG:
                #                 print(f"destroyed({len(flows)}) : {key}{' '*50}", end="\r")

                if new_key not in list(flows.keys()):
                    if len(flows) < MAX_STREAMS:
                        flows[new_key] = Flow(new_key)
                        # if DEBUG:
                        print(f"captured({len(flows)}/{MAX_STREAMS}) : {flows[new_key].speed} | {new_key[5]}{' '*50}", end="\r")
                #     else:
                #         if DEBUG:
                #             print(f"max({len(flows)})", end="\r")
                else:
                    if DEBUG:
                        print(f"refused({len(flows)}/{MAX_STREAMS}) : {new_key}{' '*50}", end="\r")

        except queue.Empty:
            continue

#%%
# ======================
# NETWORK CAPTURE
# ======================
def stdin_reader():
    for line in sys.stdin:
        m = None
        protocole = ""
        # print(f"len: {len(match_expressions)}")
        for _index_pattern in range(0, len(match_expressions)):
            protocole = list(match_expressions.keys())[_index_pattern]
            m: Match = match_expressions[protocole].match(line)
            # print(f"{protocole}: {_index_pattern} - {m}")
            if m:
                break

        if not m:
            continue

        message = m.groupdict()
        src = message.get('src', "")
        sport = message.get('sport', "0")
        dst = message.get('dst', "")
        dport = message.get('dport', "0")
        key = (src, dst, int(sport), int(dport), protocole, len(line))

        if not packet_queue.full():
            packet_queue.put(key, block=False)
            # if DEBUG:
            #     print(m.groupdict(), end="\r")

#%%
def render():
    PAUSED = DEBUG
    running = True
    while running:

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_KP_PLUS:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                    PAUSED = not PAUSED

                if event.key == pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                if event.key == pygame.K_SPACE:
                    PAUSED = not PAUSED
            if event.type == pygame.QUIT:
                running = False

        if PAUSED:
            continue

        screen.fill((0, 0, 0))
        # dt = clock.tick(60) / 1000.0 # en secondes
        dt = pygame.time.Clock().tick(60) / 1000.0 # en secondes

        for x in x_positions:
            for y in y_positions:
                current_dot:Dot = dots[(x, y)]
                current_dot.update(dt)
                screen.blit(current_dot.surface, (x, y))

        with lock:
            _index = 0
            while _index < len(flows):
                key = list(flows.keys())[_index]
                current_flow: Flow = flows[key]
                current_flow.update(dt)
                flows[key] = current_flow
                if flows[key].raise_destroy_event:
                    flows.pop(key)
                    if DEBUG:
                        print(f"destroyed({len(flows)}/{MAX_STREAMS}) : {key}{' '*50}", end="\r")
                    continue

                flow_dot: Dot = dots[(current_flow.x, current_flow.y)]
                flow_dot.update(dt, speed=current_flow.speed)#, color=current_flow.color)
                if flow_dot.glyph != current_flow.glyphs[0]:
                    # print(f"({flow_dot.x}, {flow_dot.y}) = '{current_flow.glyphs[0]}' | {current_flow.speed}")
                    flow_dot.activate(current_flow.glyphs[0], current_flow.speed, color=current_flow.color)
                    dots[(current_flow.x, current_flow.y)] = flow_dot
                _index += 1

#%%
        if DEBUG:
            if len(flows)>0:
                debug_key = list(flows.keys())[0]
                debug_flow: Flow = flows[debug_key]
                surface = renderer.render_text(f"FLOW({debug_flow.x}, {debug_flow.y}): '{debug_flow.glyphs[0]}' | {debug_flow.key}")
                screen.blit(surface, (10, (FONT_SIZE*30)))

                # debug_dot = dots[(debug_flow.x, debug_flow.y)]
                debug_dot = dots[(x_positions[0], y_positions[0])]
                surface = renderer.render_text(f"DOT({debug_dot.x}, {debug_dot.y}): '{debug_dot.glyph}' | {debug_dot.intensity}")
                screen.blit(surface, (10, (FONT_SIZE*31)))

        pygame.display.flip()

    pygame.quit()

#%%

# ======================
# MAIN
# ======================
if __name__ == "__main__":

#%%
    # Start aggregator
    threading.Thread(target=aggregator, daemon=True).start()

    # Start capture threads 
    # sudo tcpdump -l -nn -tt 
    threading.Thread(target=stdin_reader, daemon=True).start()

#%%
    for x in x_positions:
        speed, text = (0.01, "0"*len(y_positions))
        # key = (src, dst, int(sport), int(dport), protocole, min(MAX_FLOW_LENGTH, len(line)))
        # key = src, dst, sport, dport, proto, length, x, text, speed
        key = (x, 0, int(0), int(0), "TCP", len(y_positions), x, text, speed)
        if not packet_queue.full():
            packet_queue.put(key, block=False)


#%%

    # glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    # glow_surface.fill((0, 0, 0, 0))

    # Start renderer
    render()
