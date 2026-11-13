#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Patches SimpleGraphic for Windows with Unicode / Cyrillic Font Support
# ==============================================================================

import os
import sys
import re

def patch_r_font_cpp(simplegraphic_dir):
    font_cpp_path = os.path.join(simplegraphic_dir, "engine", "render", "r_font.cpp")
    if not os.path.exists(font_cpp_path):
        print(f"Error: {font_cpp_path} not found")
        return False

    with open(font_cpp_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add #include <unordered_map> if not present
    if "#include <unordered_map>" not in content:
        content = "#include <unordered_map>\n" + content

    # 2. Update struct f_fontHeight_s to use std::unordered_map<char32_t, f_glyph_s>
    struct_pattern = r'struct f_fontHeight_s \{[\s\S]*?f_glyph_s const& Glyph\(char ch\) const \{[\s\S]*?\}\s*\};'
    struct_replacement = '''struct f_fontHeight_s {
	r_tex_c* tex;
	int		height;
	int		numGlyph;
	std::unordered_map<char32_t, f_glyph_s> glyphs;
	f_glyph_s defGlyph{0.0f, 0.0f, 0.0f, 0.0f, 0, 0, 0};

	bool HasGlyph(char32_t ch) const {
		auto it = glyphs.find(ch);
		return it != glyphs.end() && (it->second.width > 0 || ch == U' ');
	}

	f_glyph_s const& Glyph(char32_t ch) const {
		auto it = glyphs.find(ch);
		if (it != glyphs.end()) {
			return it->second;
		}
		return defGlyph;
	}
};'''
    content, count = re.subn(struct_pattern, struct_replacement, content, count=1)
    if count == 0:
        print("Warning: f_fontHeight_s pattern not matched directly, trying fallback...")

    # 3. Update GLYPH parsing in TGF loader
    loader_pattern = r'else if \(fh && sscanf\(sub\.c_str\(\), "GLYPH %u %u %u %d %d;", &x, &y, &w, &sl, &sr\) == 5\) \{[\s\S]*?fh->numGlyph\+\+;[\s\S]*?glyph->spRight = sr;\s*\}'
    loader_replacement = '''int cp;
		if (fh && sscanf(sub.c_str(), "GLYPH %u %u %u %u %d %d;", &cp, &x, &y, &w, &sl, &sr) == 6) {
			// Explicit codepoint (Unicode / Cyrillic extension)
			f_glyph_s glyph;
			glyph.tcLeft = (float)x / fh->tex->fileWidth;
			glyph.tcRight = (float)(x + w) / fh->tex->fileWidth;
			glyph.tcTop = (float)y / fh->tex->fileHeight;
			glyph.tcBottom = (float)(y + fh->height) / fh->tex->fileHeight;
			glyph.width = w;
			glyph.spLeft = sl;
			glyph.spRight = sr;
			fh->glyphs[(char32_t)cp] = glyph;
			if (cp >= fh->numGlyph) fh->numGlyph = cp + 1;
		}
		else if (fh && sscanf(sub.c_str(), "GLYPH %u %u %u %d %d;", &x, &y, &w, &sl, &sr) == 5) {
			// Legacy sequential ASCII
			f_glyph_s glyph;
			glyph.tcLeft = (float)x / fh->tex->fileWidth;
			glyph.tcRight = (float)(x + w) / fh->tex->fileWidth;
			glyph.tcTop = (float)y / fh->tex->fileHeight;
			glyph.tcBottom = (float)(y + fh->height) / fh->tex->fileHeight;
			glyph.width = w;
			glyph.spLeft = sl;
			glyph.spRight = sr;
			fh->glyphs[(char32_t)fh->numGlyph++] = glyph;
		}'''
    content = re.sub(loader_pattern, loader_replacement, content, count=1)

    # 4. Update measureCodepoint and drawCodepoint lambdas
    content = content.replace(
        "auto& glyph = glyphFh->Glyph((char)(unsigned char)cp);",
        "auto& glyph = glyphFh->Glyph(cp);"
    )
    content = content.replace(
        "auto& glyph = fh->Glyph((char)(unsigned char)cp);",
        "auto& glyph = fh->Glyph(cp);"
    )

    # 6. Replace tofu checks with HasGlyph(ch)
    content = content.replace(
        "else if (ch >= (unsigned)fh->numGlyph) {",
        "else if (!fh->HasGlyph(ch)) {"
    )
    content = content.replace(
        "else if (*I >= (unsigned)fh->numGlyph) {",
        "else if (!fh->HasGlyph(*I)) {"
    )
    content = content.replace(
        "if (ch >= (unsigned)fh->numGlyph) {",
        "if (!fh->HasGlyph(ch)) {"
    )

    with open(font_cpp_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Successfully patched {font_cpp_path} for Cyrillic support!")
    return True

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upstream", "SimpleGraphic")
    print(f"=== Patching SimpleGraphic in {target_dir} ===")
    patch_r_font_cpp(target_dir)
