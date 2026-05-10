import os
import pygame
import pygame.freetype
from fontTools.ttLib import TTFont

class MultiFontRenderer:
    def __init__(self, font_paths, size, color=(255, 255, 255)):
        [print(f"NOT FOUND: {path}") for path in font_paths if not os.path.exists(path)]
        self.font_paths = font_paths
        self.fonts = [pygame.freetype.Font(path, size) for path in font_paths if os.path.exists(path)]
        self.color = color

        # Cache : (char, font_index) -> surface
        self.glyph_cache = {}

        # Cache : char -> font_index
        self.char_font_map = {}

    def rgba_normalise_255(self, couleur, alpha=1.0):
        if len(couleur) != 4:
            couleur = (*couleur, alpha)

        def clamp(x):
            return max(0, min(1, x))

        return tuple(round(clamp(x) * 255) for x in couleur)


    def has_glyph(self, ttf_path, char):
        for i in range(0, 9):
            font = TTFont(ttf_path, fontNumber=i)
            codepoint = ord(char)

            for table in font["cmap"].tables:
                if codepoint in table.cmap:
                    return True
        return False

    def find_font_for_char(self, char):
        if char in self.char_font_map:
            return self.char_font_map[char]

        for i, font in enumerate(self.font_paths):
            if self.has_glyph(font, char):
                self.char_font_map[char] = i
                return i

        self.char_font_map[char] = 0
        return 0

    def render_char(self, char, color: tuple[float, float, float] | tuple[float, float, float, float] | None = None, index: int=0, all: int=0):
        # color = self.rgba_normalise_255(color) if color is not None else self.color
        color = color if color is not None else self.color
        # on passe d'abord par le cache        
        for font_index in [*range(0, len(self.font_paths)), 0]:
            key = (char, font_index)
            if key in self.glyph_cache:
                return self.glyph_cache[key]

        font_index = self.find_font_for_char(char)
        print(f"[{index}/{all}] - {hex(ord(char))} - {char} - fonts[{font_index}]{' '*50}", end="\r")
        font = self.fonts[font_index]
        surface, _ = font.render(char, color)

        self.glyph_cache[key] = surface
        return surface

    def render_text(self, text):
        all = len(text)
        glyphs = [self.render_char(c, index=i, all=all) for i, c in enumerate(text)]

        width = sum(g.get_width() for g in glyphs)
        height = max(g.get_height() for g in glyphs)

        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        x = 0
        max_h = 0
        for g in glyphs:
            surface.blit(g, (x, 0))
            x += g.get_rect().width
            max_h = max(max_h, g.get_rect().height)
            
        return surface