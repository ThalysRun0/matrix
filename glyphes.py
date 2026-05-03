#%%
def unicode_range(start, end):
    return [chr(code) for code in range(start, end + 1)]

languages = {}

# digits
languages["digits"] = (
    unicode_range(0x0030, 0x0039)
)

# European
languages["ascii"] = (
    unicode_range(0x0061, 0x007A) + # lower
    unicode_range(0x0041, 0x005A)   # upper
)

# Hiragana
languages["hiragana"] = (
    unicode_range(0x3041, 0x3096)
)

# Katakana
languages["katakana"] = (
    unicode_range(0x30A1, 0x30FE)
)

# Cyrillique (inclut lettres de base + étendu)
languages["cyrillic"] = (
    unicode_range(0x0400, 0x04FF) +   # Cyrillique de base
    unicode_range(0x0500, 0x052F)     # Cyrillique étendu
)

# Hébreu
languages["hebrew"] = (
    # unicode_range(0x0591, 0x05c7) +
    unicode_range(0x05d0, 0x05ea)
)

# Arabe
languages["arabic"] = (
    unicode_range(0x0606, 0x061b) +   # Arabe plage début
    unicode_range(0x0620, 0x066f) +   # Arabe plage ...
    unicode_range(0x0676, 0x06d3) +   # Arabe plage ...
    unicode_range(0x06ee, 0x06ff) +   # Arabe plage ...
    unicode_range(0x0750, 0x077F) +   # Arabe étendu A
    unicode_range(0x08A0, 0x08be)     # Arabe étendu B
)

# Coréen (Hangul)
languages["korean"] = (
    # unicode_range(0x1100, 0x11FF)    # Jamo
    unicode_range(0x3131, 0x318e)    # Compatibilité Jamo
    # unicode_range(0xAC00, 0xd7a3)     # Syllabes complètes
)

# # %% exemple d'usage
# source = languages["korean"]
# source_pairs = [(f"{ord(c):#06x}", c) for c in source]
# source_pairs

# # %%
