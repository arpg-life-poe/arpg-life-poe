#include "FontRenderer.hpp"
#include "TgaImage.hpp"

#import <CoreText/CoreText.h>
#import <CoreGraphics/CoreGraphics.h>
#import <CoreFoundation/CoreFoundation.h>
#import <Foundation/Foundation.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <memory>
#include <vector>
#include <unordered_map>

namespace {

inline uint32_t decodeUtf8(const std::string& text, size_t& i) {
    if (i >= text.size()) return 0;
    unsigned char c = static_cast<unsigned char>(text[i]);
    if (c < 0x80) {
        ++i;
        return c;
    }
    if ((c & 0xE0) == 0xC0) {
        if (i + 1 < text.size()) {
            uint32_t cp = ((c & 0x1F) << 6) | (static_cast<unsigned char>(text[i + 1]) & 0x3F);
            i += 2;
            return cp;
        }
    } else if ((c & 0xF0) == 0xE0) {
        if (i + 2 < text.size()) {
            uint32_t cp = ((c & 0x0F) << 12) |
                          ((static_cast<unsigned char>(text[i + 1]) & 0x3F) << 6) |
                          (static_cast<unsigned char>(text[i + 2]) & 0x3F);
            i += 3;
            return cp;
        }
    } else if ((c & 0xF8) == 0xF0) {
        if (i + 3 < text.size()) {
            uint32_t cp = ((c & 0x07) << 18) |
                          ((static_cast<unsigned char>(text[i + 1]) & 0x3F) << 12) |
                          ((static_cast<unsigned char>(text[i + 2]) & 0x3F) << 6) |
                          (static_cast<unsigned char>(text[i + 3]) & 0x3F);
            i += 4;
            return cp;
        }
    }
    ++i;
    return c;
}

struct Glyph {
    float tcLeft = 0.0f;
    float tcRight = 0.0f;
    float tcTop = 0.0f;
    float tcBottom = 0.0f;
    int pixelX = 0;
    int pixelY = 0;
    int width = 0;
    int spLeft = 0;
    int spRight = 0;
};

struct DynamicGlyph {
    mutable SDL_Texture* texture = nullptr;
    int advance = 0;
    int pixelWidth = 0;
    int pixelHeight = 0;
    mutable std::vector<uint32_t> pixels{};

    ~DynamicGlyph() {
        if (texture) {
            SDL_DestroyTexture(texture);
            texture = nullptr;
        }
    }

    DynamicGlyph() = default;
    DynamicGlyph(const DynamicGlyph&) = delete;
    DynamicGlyph& operator=(const DynamicGlyph&) = delete;
    DynamicGlyph(DynamicGlyph&& other) noexcept
        : texture(other.texture),
          advance(other.advance),
          pixelWidth(other.pixelWidth),
          pixelHeight(other.pixelHeight),
          pixels(std::move(other.pixels)) {
        other.texture = nullptr;
    }
    DynamicGlyph& operator=(DynamicGlyph&& other) noexcept {
        if (this != &other) {
            if (texture) {
                SDL_DestroyTexture(texture);
            }
            texture = other.texture;
            advance = other.advance;
            pixelWidth = other.pixelWidth;
            pixelHeight = other.pixelHeight;
            pixels = std::move(other.pixels);
            other.texture = nullptr;
        }
        return *this;
    }
};

struct FontHeight {
    std::filesystem::path tgaPath;
    SDL_Texture* texture = nullptr;
    int atlasWidth = 0;
    int atlasHeight = 0;
    int height = 0;
    int numGlyph = 0;
    std::array<Glyph, 128> glyphs{};
    Glyph defGlyph{};
    CTFontRef ctFont = nullptr;
    mutable std::unordered_map<uint32_t, DynamicGlyph> dynamicGlyphs{};

    const Glyph& glyph(unsigned char ch) const {
        if (ch >= static_cast<unsigned char>(numGlyph)) {
            return defGlyph;
        }
        return glyphs[ch];
    }

    ~FontHeight() {
        if (texture) {
            SDL_DestroyTexture(texture);
            texture = nullptr;
        }
        dynamicGlyphs.clear();
        if (ctFont) {
            CFRelease(ctFont);
            ctFont = nullptr;
        }
    }

    bool ensureTexture(SDL_Renderer* renderer) {
        if (texture || tgaPath.empty()) {
            return texture != nullptr;
        }
        texture = loadTgaTexture(renderer, tgaPath, atlasWidth, atlasHeight);
        if (!texture || atlasWidth <= 0 || atlasHeight <= 0) {
            return false;
        }
        for (int i = 0; i < numGlyph; ++i) {
            Glyph& g = glyphs[i];
            g.tcLeft = static_cast<float>(g.pixelX) / atlasWidth;
            g.tcRight = static_cast<float>(g.pixelX + g.width) / atlasWidth;
            g.tcTop = static_cast<float>(g.pixelY) / atlasHeight;
            g.tcBottom = static_cast<float>(g.pixelY + height) / atlasHeight;
        }
        return true;
    }

    void rasterizeGlyphToMemory(CTFontRef font, CGGlyph glyph, DynamicGlyph& dg) const {
        CGFloat ascent = CTFontGetAscent(font);
        CGFloat descent = CTFontGetDescent(font);
        int w = std::max(1, dg.advance);
        int h = std::max(1, static_cast<int>(std::ceil(ascent + descent)));
        dg.pixelWidth = w;
        dg.pixelHeight = h;
        dg.pixels.assign(w * h, 0);

        CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
        CGContextRef ctx = CGBitmapContextCreate(
            dg.pixels.data(),
            w,
            h,
            8,
            w * 4,
            colorSpace,
            kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big
        );
        if (ctx) {
            CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0);
            CGPoint pos = CGPointMake(0, descent);
            CTFontDrawGlyphs(font, &glyph, &pos, 1, ctx);
            CGContextRelease(ctx);
        }
        CGColorSpaceRelease(colorSpace);
    }

    const DynamicGlyph& getDynamicGlyph(SDL_Renderer* renderer, uint32_t cp) const {
        auto it = dynamicGlyphs.find(cp);
        if (it != dynamicGlyphs.end()) {
            if (renderer && !it->second.texture && !it->second.pixels.empty()) {
                ensureTextureForGlyph(renderer, it->second);
            }
            return it->second;
        }

        DynamicGlyph dg{};
        if (!ctFont) {
            dg.advance = std::max(1, height / 2);
            auto [inserted, _] = dynamicGlyphs.emplace(cp, std::move(dg));
            return inserted->second;
        }

        UniChar chars[2];
        int charCount = 0;
        if (cp <= 0xFFFF) {
            chars[0] = static_cast<UniChar>(cp);
            charCount = 1;
        } else {
            uint32_t temp = cp - 0x10000;
            chars[0] = static_cast<UniChar>((temp >> 10) + 0xD800);
            chars[1] = static_cast<UniChar>((temp & 0x3FF) + 0xDC00);
            charCount = 2;
        }

        CGGlyph glyph = 0;
        if (CTFontGetGlyphsForCharacters(ctFont, chars, &glyph, charCount) && glyph != 0) {
            double adv = CTFontGetAdvancesForGlyphs(ctFont, kCTFontOrientationDefault, &glyph, NULL, 1);
            dg.advance = std::max(1, static_cast<int>(std::round(adv)));
            rasterizeGlyphToMemory(ctFont, glyph, dg);
        } else {
            CFStringRef str = CFStringCreateWithCharacters(kCFAllocatorDefault, chars, charCount);
            CTFontRef fallback = str ? CTFontCreateForString(ctFont, str, CFRangeMake(0, charCount)) : nullptr;
            if (str) CFRelease(str);

            if (fallback) {
                CTFontGetGlyphsForCharacters(fallback, chars, &glyph, charCount);
                double adv = CTFontGetAdvancesForGlyphs(fallback, kCTFontOrientationDefault, &glyph, NULL, 1);
                dg.advance = std::max(1, static_cast<int>(std::round(adv)));
                rasterizeGlyphToMemory(fallback, glyph, dg);
                CFRelease(fallback);
            } else {
                dg.advance = std::max(1, height / 2);
            }
        }

        if (renderer && !dg.pixels.empty()) {
            ensureTextureForGlyph(renderer, dg);
        }

        auto [inserted, _] = dynamicGlyphs.emplace(cp, std::move(dg));
        return inserted->second;
    }

    void ensureTextureForGlyph(SDL_Renderer* renderer, const DynamicGlyph& dg) const {
        if (dg.texture || dg.pixels.empty() || dg.pixelWidth <= 0 || dg.pixelHeight <= 0) {
            return;
        }
        SDL_Texture* tex = SDL_CreateTexture(
            renderer,
            SDL_PIXELFORMAT_RGBA32,
            SDL_TEXTUREACCESS_STATIC,
            dg.pixelWidth,
            dg.pixelHeight
        );
        if (tex) {
            SDL_UpdateTexture(tex, nullptr, dg.pixels.data(), dg.pixelWidth * 4);
            SDL_SetTextureBlendMode(tex, SDL_BLENDMODE_BLEND);
            dg.texture = tex;
            dg.pixels.clear();
            dg.pixels.shrink_to_fit();
        }
    }
};

struct FontImpl {
    std::string name;
    std::vector<std::unique_ptr<FontHeight>> heights;
    std::vector<int> heightMap;
    int maxHeight = 0;

    void initCoreText() {
        bool isBold = (name.find("Bold") != std::string::npos || name.find("BOLD") != std::string::npos);
        for (auto& fh : heights) {
            CFStringRef primaryName = isBold ? CFSTR("Helvetica-Bold") : CFSTR("Helvetica");
            CTFontRef base = CTFontCreateWithName(primaryName, static_cast<CGFloat>(fh->height), NULL);
            if (!base) {
                base = CTFontCreateUIFontForLanguage(kCTFontUIFontSystem, static_cast<CGFloat>(fh->height), CFSTR("ru"));
            }
            if (base) {
                fh->ctFont = CTFontCreateForString(base, CFSTR("А"), CFRangeMake(0, 1));
                CFRelease(base);
            }
        }
    }

    bool load(const std::filesystem::path& fontsDir, const std::string& fontName) {
        name = fontName;
        const std::filesystem::path tgfPath = fontsDir / (fontName + ".tgf");
        std::ifstream tgf(tgfPath);
        if (!tgf) {
            std::fprintf(stderr, "Font metadata not found: %s\n", tgfPath.string().c_str());
            return false;
        }

        FontHeight* current = nullptr;
        std::string line;
        while (std::getline(tgf, line)) {
            unsigned h = 0;
            unsigned x = 0;
            unsigned y = 0;
            unsigned w = 0;
            int sl = 0;
            int sr = 0;
            if (std::sscanf(line.c_str(), "HEIGHT %u;", &h) == 1) {
                auto fh = std::make_unique<FontHeight>();
                fh->height = static_cast<int>(h);
                fh->tgaPath = fontsDir / (fontName + "." + std::to_string(h) + ".tga");
                maxHeight = std::max(maxHeight, fh->height);
                current = fh.get();
                heights.push_back(std::move(fh));
            } else if (current && std::sscanf(line.c_str(), "GLYPH %u %u %u %d %d;", &x, &y, &w, &sl, &sr) == 5) {
                if (current->numGlyph >= 128) {
                    continue;
                }
                Glyph& glyph = current->glyphs[current->numGlyph++];
                glyph.pixelX = static_cast<int>(x);
                glyph.pixelY = static_cast<int>(y);
                glyph.width = static_cast<int>(w);
                glyph.spLeft = sl;
                glyph.spRight = sr;
            }
        }

        if (heights.empty()) {
            return false;
        }

        initCoreText();

        heightMap.assign(static_cast<size_t>(maxHeight) + 1, 0);
        for (size_t i = 0; i < heights.size(); ++i) {
            const int gh = heights[i]->height;
            for (int h = gh; h <= maxHeight; ++h) {
                heightMap[static_cast<size_t>(h)] = static_cast<int>(i);
            }
            if (i > 0) {
                const int belowH = heights[i - 1]->height;
                const int lim = (gh - belowH - 1) / 2;
                for (int b = 0; b < lim; ++b) {
                    heightMap[static_cast<size_t>(gh - b - 1)] = static_cast<int>(i);
                }
            }
        }
        return true;
    }

    bool ensureTextures(SDL_Renderer* renderer) {
        bool ok = true;
        for (auto& entry : heights) {
            if (!entry->ensureTexture(renderer)) {
                std::fprintf(stderr, "Font atlas not found: %s\n", entry->tgaPath.string().c_str());
                ok = false;
            }
        }
        return ok;
    }

    FontHeight* findFontHeight(int height) const {
        if (heights.empty()) {
            return nullptr;
        }
        int idx = 0;
        if (height > maxHeight) {
            idx = static_cast<int>(heights.size()) - 1;
        } else if (height < 0) {
            idx = 0;
        } else {
            idx = heightMap[static_cast<size_t>(height)];
        }
        return heights[static_cast<size_t>(idx)].get();
    }

    int heightIndex(const FontHeight* fh) const {
        for (size_t i = 0; i < heights.size(); ++i) {
            if (heights[i].get() == fh) {
                return static_cast<int>(i);
            }
        }
        return 0;
    }

    int glyphAdvance(const FontHeight* fh, unsigned char ch) const {
        const Glyph& g = fh->glyph(ch);
        return g.width + g.spLeft + g.spRight;
    }

    int stringWidthInternal(const FontHeight* fh, const std::string& text, int height, float scale) const {
        float width = 0.0f;
        for (size_t i = 0; i < text.size();) {
            if (text[i] == '^') {
                if (i + 1 < text.size() && text[i + 1] >= '0' && text[i + 1] <= '9') {
                    i += 2;
                    continue;
                }
                if (i + 7 < text.size() && text[i + 1] == 'x') {
                    i += 8;
                    continue;
                }
            }
            if (text[i] == '\n') {
                break;
            }
            if (text[i] == '\t') {
                width += glyphAdvance(fh, ' ') * 4.0f * scale;
                width = std::ceil(width);
                ++i;
                continue;
            }
            uint32_t cp = decodeUtf8(text, i);
            if (cp < static_cast<uint32_t>(fh->numGlyph)) {
                width += glyphAdvance(fh, static_cast<unsigned char>(cp)) * scale;
            } else {
                const DynamicGlyph& dg = fh->getDynamicGlyph(nullptr, cp);
                width += static_cast<float>(dg.advance) * scale;
            }
            width = std::ceil(width);
        }
        return static_cast<int>(width);
    }

    int stringWidth(int height, const std::string& text) const {
        FontHeight* fh = findFontHeight(height);
        if (!fh) {
            return 0;
        }
        const float scale = static_cast<float>(height) / fh->height;
        int maxWidth = 0;
        size_t start = 0;
        while (start <= text.size()) {
            size_t end = text.find('\n', start);
            if (end == std::string::npos) {
                end = text.size();
            }
            if (end > start) {
                maxWidth = std::max(maxWidth, stringWidthInternal(fh, text.substr(start, end - start), height, scale));
            }
            if (end == text.size()) {
                break;
            }
            start = end + 1;
        }
        return maxWidth;
    }

    size_t stringCursorInternal(const FontHeight* fh, const std::string& text, int height, float scale, int curX) const {
        float x = 0.0f;
        size_t i = 0;
        while (i < text.size() && text[i] != '\n') {
            if (text[i] == '^') {
                if (i + 1 < text.size() && text[i + 1] >= '0' && text[i + 1] <= '9') {
                    i += 2;
                    continue;
                }
                if (i + 7 < text.size() && text[i + 1] == 'x') {
                    i += 8;
                    continue;
                }
            }
            size_t prev_i = i;
            uint32_t cp = decodeUtf8(text, i);
            float adv = 0.0f;
            if (cp == '\t') {
                adv = glyphAdvance(fh, ' ') * 4.0f * scale;
            } else if (cp < static_cast<uint32_t>(fh->numGlyph)) {
                adv = glyphAdvance(fh, static_cast<unsigned char>(cp)) * scale;
            } else {
                const DynamicGlyph& dg = fh->getDynamicGlyph(nullptr, cp);
                adv = static_cast<float>(dg.advance) * scale;
            }
            x += adv;
            x = std::ceil(x);
            if (curX <= x) {
                return prev_i;
            }
        }
        return i;
    }

    int stringCursorIndex(int height, const std::string& text, int curX, int curY) const {
        FontHeight* fh = findFontHeight(height);
        if (!fh) {
            return 0;
        }
        const float scale = static_cast<float>(height) / fh->height;
        size_t index = 0;
        int lineY = height;
        size_t start = 0;
        while (start <= text.size()) {
            size_t end = text.find('\n', start);
            if (end == std::string::npos) {
                end = text.size();
            }
            const size_t local = stringCursorInternal(fh, text.substr(start, end - start), height, scale, curX);
            index = start + local;
            if (curY <= lineY) {
                break;
            }
            if (end == text.size()) {
                break;
            }
            start = end + 1;
            lineY += height;
        }
        return static_cast<int>(index);
    }

    void drawCodepoint(
        SDL_Renderer* renderer,
        FontHeight*& currentTexture,
        float& x,
        float y,
        const FontHeight* fh,
        int drawHeight,
        float scale,
        int yShift,
        unsigned char ch,
        SDL_FColor color
    ) const {
        const float cpY = y + static_cast<float>(yShift);
        if (currentTexture != fh) {
            currentTexture = const_cast<FontHeight*>(fh);
        }
        const Glyph& glyph = fh->glyph(ch);
        x += glyph.spLeft * scale;
        if (glyph.width > 0) {
            const float w = glyph.width * scale;
            SDL_FRect dest{x, cpY, w, static_cast<float>(drawHeight)};
            SDL_FRect src{
                glyph.tcLeft * fh->atlasWidth,
                glyph.tcTop * fh->atlasHeight,
                (glyph.tcRight - glyph.tcLeft) * fh->atlasWidth,
                (glyph.tcBottom - glyph.tcTop) * fh->atlasHeight,
            };
            SDL_SetTextureColorModFloat(fh->texture, color.r, color.g, color.b);
            SDL_SetTextureAlphaModFloat(fh->texture, color.a);
            SDL_RenderTexture(renderer, fh->texture, &src, &dest);
            x += w;
        }
        x += glyph.spRight * scale;
        x = std::ceil(x);
    }

    void drawDynamicCodepoint(
        SDL_Renderer* renderer,
        float& x,
        float y,
        const FontHeight* fh,
        int drawHeight,
        float scale,
        uint32_t cp,
        SDL_FColor color
    ) const {
        const DynamicGlyph& dg = fh->getDynamicGlyph(renderer, cp);
        if (dg.texture && dg.pixelWidth > 0 && dg.pixelHeight > 0) {
            const float w = static_cast<float>(dg.pixelWidth) * scale;
            const float h = static_cast<float>(dg.pixelHeight) * scale;
            SDL_FRect dest{x, y, w, h};
            SDL_SetTextureColorModFloat(dg.texture, color.r, color.g, color.b);
            SDL_SetTextureAlphaModFloat(dg.texture, color.a);
            SDL_RenderTexture(renderer, dg.texture, nullptr, &dest);
        }
        x += static_cast<float>(dg.advance) * scale;
        x = std::ceil(x);
    }

    void drawTextLine(
        SDL_Renderer* renderer,
        float x,
        float y,
        const std::string& align,
        int height,
        const std::string& text,
        SDL_FColor color,
        int screenWidth
    ) const {
        FontHeight* fh = findFontHeight(height);
        if (!fh || !fh->texture) {
            return;
        }
        const float scale = static_cast<float>(height) / fh->height;

        if (align == "CENTER") {
            x = std::floor((screenWidth - stringWidthInternal(fh, text, height, scale)) / 2.0f + x);
        } else if (align == "RIGHT") {
            x = std::floor(screenWidth - stringWidthInternal(fh, text, height, scale) - x);
        } else if (align == "CENTER_X") {
            x = std::floor(x - stringWidthInternal(fh, text, height, scale) / 2.0f);
        } else if (align == "RIGHT_X") {
            x = std::floor(x - stringWidthInternal(fh, text, height, scale));
        }
        x = std::round(x);

        FontHeight* currentTexture = nullptr;
        for (size_t i = 0; i < text.size();) {
            if (text[i] == '^') {
                if (i + 1 < text.size() && text[i + 1] >= '0' && text[i + 1] <= '9') {
                    i += 2;
                    continue;
                }
                if (i + 7 < text.size() && text[i + 1] == 'x') {
                    i += 8;
                    continue;
                }
            }
            if (text[i] == '\t') {
                x += glyphAdvance(fh, ' ') * 4.0f * scale;
                ++i;
                continue;
            }
            uint32_t cp = decodeUtf8(text, i);
            if (cp < static_cast<uint32_t>(fh->numGlyph)) {
                drawCodepoint(renderer, currentTexture, x, y, fh, height, scale, 0, static_cast<unsigned char>(cp), color);
            } else {
                drawDynamicCodepoint(renderer, x, y, fh, height, scale, cp, color);
            }
        }
    }

    void drawString(
        SDL_Renderer* renderer,
        float x,
        float y,
        const std::string& align,
        int height,
        const std::string& text,
        SDL_FColor color,
        int screenWidth
    ) const {
        if (text.empty()) {
            return;
        }
        size_t start = 0;
        float lineY = y;
        while (start <= text.size()) {
            size_t end = text.find('\n', start);
            if (end == std::string::npos) {
                end = text.size();
            }
            if (end > start) {
                drawTextLine(renderer, x, lineY, align, height, text.substr(start, end - start), color, screenWidth);
            }
            lineY += height;
            if (end == text.size()) {
                break;
            }
            start = end + 1;
        }
    }
};
}

struct FontRenderer::Impl : FontImpl {};

void FontRenderer::setFontsDirectory(std::filesystem::path path) {
    fontsDirectory = std::move(path);
    cache.clear();
}

void FontRenderer::setScreenWidth(int width) {
    screenWidth = width;
}

std::string FontRenderer::resolveFontName(const std::string& fontAlias) {
    if (fontAlias == "FIXED") {
        return "Bitstream Vera Sans Mono";
    }
    if (fontAlias == "VAR BOLD") {
        return "Liberation Sans Bold";
    }
    if (fontAlias == "VAR") {
        return "Liberation Sans";
    }
    if (fontAlias == "FONTIN SC ITALIC") {
        return "Fontin SmallCaps Italic";
    }
    if (fontAlias == "FONTIN SC") {
        return "Fontin SmallCaps";
    }
    if (fontAlias == "FONTIN ITALIC") {
        return "Fontin Italic";
    }
    if (fontAlias == "FONTIN") {
        return "Fontin";
    }
    return fontAlias;
}

std::shared_ptr<FontRenderer::Impl> FontRenderer::getFont(const std::string& fontAlias) {
    auto it = cache.find(fontAlias);
    if (it != cache.end()) {
        return it->second;
    }
    auto font = std::make_shared<Impl>();
    if (!font->load(fontsDirectory, resolveFontName(fontAlias))) {
        return nullptr;
    }
    cache.emplace(fontAlias, font);
    return font;
}

double FontRenderer::stringWidth(double height, const std::string& fontAlias, const std::string& text) {
    auto font = getFont(fontAlias);
    if (!font) {
        return 0.0;
    }
    return font->stringWidth(static_cast<int>(std::lround(height)), text);
}

int FontRenderer::stringCursorIndex(double height, const std::string& fontAlias, const std::string& text, int curX, int curY) {
    auto font = getFont(fontAlias);
    if (!font) {
        return 0;
    }
    return font->stringCursorIndex(static_cast<int>(std::lround(height)), text, curX, curY);
}

void FontRenderer::drawString(
    SDL_Renderer* renderer,
    float x,
    float y,
    const std::string& align,
    double height,
    const std::string& fontAlias,
    const std::string& text,
    SDL_FColor color
) {
    auto font = getFont(fontAlias);
    if (!font) {
        return;
    }
    font->ensureTextures(renderer);
    font->drawString(renderer, x, y, align, static_cast<int>(std::lround(height)), text, color, screenWidth);
}
