import sys, re
from re import Match
import threading
import time
import random
import queue

import glyphes
from pygameMultiFontRenderer import MultiFontRenderer
import pygame

from scapy.all import sniff, IP, TCP, UDP, ICMP

# ======================
# CONFIG
# ======================

DEBUG = False

IFACES = ['enp6s0', 'wlp5s0']
# IFACES = ['eth0', 'wlan0']
BUFFER_SIZE = 1000
MAX_STREAMS = 48

GLYPHS = (
    glyphes.languages["hiragana"] + 
    glyphes.languages["ascii"] + 
    glyphes.languages["katakana"] + 
    # glyphes.languages["korean"] +
    # glyphes.languages["hebrew"] +
    glyphes.languages["ascii"] + 
    glyphes.languages["digits"] +
    glyphes.languages["ascii"]
)

SCREEN_WIDTH = 350
SCREEN_HEIGHT = 600
FONT_SIZE = 18

# ======================
# DATA STRUCTURES
# ======================

packet_queue = queue.Queue(maxsize=BUFFER_SIZE)

flows = {}
lock = threading.Lock()

# ---------- Font ----------
# IMPORTANT : utiliser une police qui supporte hiragana
font_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.ttf",
    # "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
]

# ---------- Init ----------
pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Matrix Rain Code")
clock = pygame.time.Clock()

renderer = MultiFontRenderer(font_paths, size=FONT_SIZE)
print(f"Generate and Cache Glyphs len({len(GLYPHS)})")
renderer.render_text(GLYPHS) # on charge en cache la totalité des glyphs avant de lancer le screen
print(f"Let's Go !{' '*50}")

class Flow:
    def __init__(self, key, x):
        self.key = key
        src, dst, sport, dport, proto, length = key
        self.intensity = 255
        # self.speed = random.uniform(50, self.length % 200)
        self.speed = random.uniform(50, 200)
        self.length = length #random.randint(5, 20)
        # self.y = random.uniform(-SCREEN_HEIGHT, 0)
        self.y = SCREEN_HEIGHT # - (self.length * FONT_SIZE)
        self.x = x
        self.last_update = time.time()
        # 🔥 buffer de glyphes stable
        self.glyphs = [random.choice(GLYPHS) for _ in range(self.length)]
        self.spawn_time = time.time()

        # contrôle du rafraîchissement des glyphes
        self.last_glyph_update = time.time()
        self.raise_destroy_event = False
        self.destroyable = False

    def update(self):
        now = time.time()
        # dt = min(now - self.last_update, 0.05)
        dt = min(now - self.last_update, 0.5)

        self.y += self.speed * dt
        self.intensity *= 0.97

        # 🔥 rotation lente des glyphes (effet Matrix réaliste)
        if now - self.last_glyph_update > 0.1:
            self.glyphs.pop()
            self.glyphs.insert(0, random.choice(GLYPHS))
            self.last_glyph_update = now

        self.last_update = now

        if self.y > SCREEN_HEIGHT: # si on est arrivé en bas de l'écran
            self.y = -self.length * FONT_SIZE  # on repart en haut de l'écran
            self.intensity = 1.0


# ======================
# NETWORK CAPTURE
# ======================

def packet_handler(pkt):
    try:
        if IP not in pkt:
            return

        ip = pkt[IP]

        proto = "OTHER"
        sport, dport = 0, 0

        if TCP in pkt:
            proto = "TCP"
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
        elif UDP in pkt:
            proto = "UDP"
            sport = pkt[UDP].sport
            dport = pkt[UDP].dport
        elif ICMP in pkt:
            proto = "ICMP"

        key = (ip.src, ip.dst, sport, dport, proto)

        if not packet_queue.full():
            packet_queue.put(key)

    except Exception:
        pass


def capture_thread(iface):
    sniff(iface=iface, prn=packet_handler, store=False)

# ======================
# FLOW AGGREGATION
# ======================

def aggregator():
    while True:
        try:
            key = packet_queue.get(timeout=1)

            with lock:
                if len(flows)>0:
                    if len(flows) >= MAX_STREAMS:
                        oldest_key = min(flows, key=lambda k: flows[k].spawn_time)
                        flow: Flow = flows[oldest_key]
                        if flow.raise_destroy_event and flow.destroyable:
                            del flows[oldest_key]
                            if DEBUG:
                                print(f"Flow destroyed : {oldest_key}")
                        else:
                            flow.raise_destroy_event = True

                if key not in flows:
                    if len(flows) < MAX_STREAMS:
                        x = ((random.uniform(0, len(flows)-1) % (SCREEN_WIDTH // FONT_SIZE))) * FONT_SIZE
                        flows[key] = Flow(key, x)

        except queue.Empty:
            continue

# sudo tcpdump -l -nn -tt
#%%
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

        # print(m.groupdict())
        message = m.groupdict()
        src = message.get('src', "")
        sport = message.get('sport', "0")
        dst = message.get('dst', "")
        dport = message.get('dport', "0")

        key = (src, dst, int(sport), int(dport), protocole, len(line))

        if not packet_queue.full():
            packet_queue.put(key)
            if DEBUG:
                print(m.groupdict())

def render():

    running = True
    while running:
        screen.fill((0, 0, 0))

        with lock:
            keys = list(flows.keys())

            for i, key in enumerate(keys):
                flow: Flow = flows[key]
                
                if flow.raise_destroy_event and (flow.y <= 0):
                    flow.destroyable = True

                flow.update()

                proto = key[4]
                if proto == "TCP":
                    color = (0, 255, 0)
                elif proto == "TCP6":
                    color = (0, 255, 128)
                elif proto == "ARP":
                    color = (128, 255, 0)
                else:
                    color = (128, 255, 128)

                for j in range(flow.length):
                    char = flow.glyphs[j]
                    y = flow.y + j * FONT_SIZE

                    intensity = max(0, min(255, ((flow.intensity * 2) * (255 - j / (flow.length / FONT_SIZE)))))

                    if j >= flow.length-1:
                        _color = (204, 255, 204, max(0, min(255, (intensity * 3))))  # tête brillante
                        # glow = renderer.render_char(char, (0, 255, 0))
                        # glow.set_alpha(80)
                        # # dessiné sur surface glow
                        # glow_surface.blit(glow, (flow.x, y))

                    else:
                        # print(intensity)
                        _color = (*color, intensity)

                    surface = renderer.render_char(char)
                    surface = surface.copy()

                    tint = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                    # color = (*color, intensity) if len(color)<4 else color
                    tint.fill(_color)

                    surface.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(surface, (flow.x, y))

                    # # downscale → upscale = blur cheap
                    # small = pygame.transform.smoothscale(glow_surface, (SCREEN_WIDTH//4, SCREEN_HEIGHT//4))
                    # blur = pygame.transform.smoothscale(small, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    # screen.blit(blur, (0, 0), special_flags=pygame.BLEND_ADD)
                    
        if DEBUG:
            surface = renderer.render_text(str(len(flows)))
            screen.blit(surface, (10, 10))
            if len(flows)>0:
                surface = renderer.render_text("00 "+str(round(flows[keys[0]].y)))
                screen.blit(surface, (10, 10+(FONT_SIZE*1)))
                surface = renderer.render_text(str("Destoy "+str(flows[keys[0]].raise_destroy_event)))
                screen.blit(surface, (10, 10+(FONT_SIZE*2)))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    # Start capture threads
    # for iface in IFACES:
    #     t = threading.Thread(target=capture_thread, args=(iface,), daemon=True)
    #     t.start()
    threading.Thread(target=stdin_reader, daemon=True).start()

    # Start aggregator
    threading.Thread(target=aggregator, daemon=True).start()


    glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    glow_surface.fill((0, 0, 0, 0))

    # Start renderer
    render()

# #%%
# couleur = (0.8, 1.0, 0.8)
# alpha = 1.0
# (*couleur, alpha)

# #%%
# import freetype
# from freetype import Charmap, Face

# face: Face = freetype.Face("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2)

# #%%
# hex(ord('に'))

# #%%
# g_index = face.get_char_index('に')


# #%%
# # for glyphe, i in face.get_chars():
# #     print(i)

# # for item in face.charmaps:
# #     charmap: Charmap = item
# #     print(charmap)
# #     # print(f"charmap = (id={charmap.cmap_language_id}, encoding_name={charmap.encoding_name}, size={charmap.__sizeof__()}")
# #     # print(charmap)

# %%

# #%%
# intensity = 255
# color = (1, 255, 0)
# (*color, intensity)

# #%%