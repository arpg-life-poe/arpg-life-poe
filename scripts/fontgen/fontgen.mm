// ==============================================================================
// Path of Building — ARPG-Life Edition
// Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
// Project: https://arpg-life.ru
//
// Cyrillic Font Generator for SimpleGraphic Windows runtime (.tgf + .tga)
// Uses CoreGraphics and CoreText to rasterize perfect Cyrillic glyphs into font atlases.
// ==============================================================================

#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <CoreText/CoreText.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <cmath>
#include <filesystem>
#include <algorithm>

namespace fs = std::filesystem;

#pragma pack(push, 1)
struct TGAHeader {
    uint8_t  idLen;
    uint8_t  colorMapType;
    uint8_t  imgType;
    uint16_t colorMapIndex;
    uint16_t colorMapLen;
    uint8_t  colorMapDepth;
    uint16_t xOrigin, yOrigin;
    uint16_t width, height;
    uint8_t  depth;
    uint8_t  descriptor;
};
#pragma pack(pop)

// Decode RLE or Raw TGA to 32-bit BGRA buffer (top-down)
bool LoadTGA(const std::string& path, int& outW, int& outH, std::vector<uint32_t>& outPixels) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;

    TGAHeader hdr;
    in.read(reinterpret_cast<char*>(&hdr), sizeof(hdr));
    if (!in) return false;

    outW = hdr.width;
    outH = hdr.height;
    int bpp = hdr.depth;
    if (bpp != 32 && bpp != 24) {
        std::cerr << "Unsupported BPP: " << bpp << " in " << path << "\n";
        return false;
    }

    if (hdr.idLen > 0) {
        in.seekg(hdr.idLen, std::ios::cur);
    }

    int comp = bpp / 8;
    int totalPixels = outW * outH;
    outPixels.resize(totalPixels);

    std::vector<uint8_t> rawDat(totalPixels * 4, 0);

    bool isRLE = (hdr.imgType & 8) != 0;
    bool flipV = !(hdr.descriptor & 0x20); // bottom-up if true

    if (isRLE) {
        for (int row = 0; row < outH; ++row) {
            int actualRow = flipV ? (outH - 1 - row) : row;
            uint32_t* rowPtr = &outPixels[actualRow * outW];
            int x = 0;
            while (x < outW) {
                uint8_t rleHdr = 0;
                in.read(reinterpret_cast<char*>(&rleHdr), 1);
                int count = (rleHdr & 0x7F) + 1;
                if (rleHdr & 0x80) {
                    uint8_t px[4] = {255, 255, 255, 0};
                    in.read(reinterpret_cast<char*>(px), comp);
                    uint32_t val = (uint32_t)px[0] | ((uint32_t)px[1] << 8) | ((uint32_t)px[2] << 16) | ((uint32_t)(comp == 4 ? px[3] : 255) << 24);
                    for (int c = 0; c < count && x < outW; ++c, ++x) {
                        rowPtr[x] = val;
                    }
                } else {
                    for (int c = 0; c < count && x < outW; ++c, ++x) {
                        uint8_t px[4] = {255, 255, 255, 0};
                        in.read(reinterpret_cast<char*>(px), comp);
                        rowPtr[x] = (uint32_t)px[0] | ((uint32_t)px[1] << 8) | ((uint32_t)px[2] << 16) | ((uint32_t)(comp == 4 ? px[3] : 255) << 24);
                    }
                }
            }
        }
    } else {
        for (int row = 0; row < outH; ++row) {
            int actualRow = flipV ? (outH - 1 - row) : row;
            uint32_t* rowPtr = &outPixels[actualRow * outW];
            for (int x = 0; x < outW; ++x) {
                uint8_t px[4] = {255, 255, 255, 0};
                in.read(reinterpret_cast<char*>(px), comp);
                rowPtr[x] = (uint32_t)px[0] | ((uint32_t)px[1] << 8) | ((uint32_t)px[2] << 16) | ((uint32_t)(comp == 4 ? px[3] : 255) << 24);
            }
        }
    }

    return true;
}

// Save 32-bit BGRA uncompressed TGA (top-down)
bool SaveTGA(const std::string& path, int w, int h, const std::vector<uint32_t>& pixels) {
    std::ofstream out(path, std::ios::binary);
    if (!out) return false;

    TGAHeader hdr{};
    hdr.imgType = 2; // Uncompressed true-color
    hdr.width = (uint16_t)w;
    hdr.height = (uint16_t)h;
    hdr.depth = 32;
    hdr.descriptor = 0x28; // top-down, 8-bit alpha

    out.write(reinterpret_cast<const char*>(&hdr), sizeof(hdr));
    out.write(reinterpret_cast<const char*>(pixels.data()), pixels.size() * sizeof(uint32_t));
    return true;
}

struct AddedGlyph {
    uint32_t cp;
    int x;
    int y;
    int w;
    int sl;
    int sr;
};

// Map PoB font name to macOS font name
NSString* GetMacOSFontName(const std::string& fontName) {
    if (fontName.find("Bold") != std::string::npos) {
        return @"Arial-BoldMT";
    } else if (fontName.find("Italic") != std::string::npos) {
        return @"Arial-ItalicMT";
    } else if (fontName.find("Mono") != std::string::npos) {
        return @"Menlo-Regular";
    } else {
        return @"ArialMT";
    }
}

// Generate Cyrillic extension for a single font height
bool ProcessFontHeight(
    const std::string& tgaPath,
    int fontHeight,
    NSString* fontFaceName,
    std::vector<AddedGlyph>& outGlyphs
) {
    int oldW = 0, oldH = 0;
    std::vector<uint32_t> oldPixels;
    if (!LoadTGA(tgaPath, oldW, oldH, oldPixels)) {
        std::cerr << "Failed to load TGA: " << tgaPath << "\n";
        return false;
    }

    // Characters to include:
    // Russian uppercase: U+0410..U+042F, Ё (0x0401)
    // Russian lowercase: U+0430..U+044F, ё (0x0451)
    // Ukrainian/Belarusian extras: 0x0406 (І), 0x0456 (і), 0x0407 (Ї), 0x0457 (ї), 0x0404 (Є), 0x0454 (є), 0x0490 (Ґ), 0x0491 (ґ), 0x040E (Ў), 0x045E (ў)
    // Punctuation & symbols: « (0xAB), » (0xBB), — (0x2014), – (0x2013), … (0x2026), № (0x2116), • (0x2022)
    std::vector<uint32_t> codepoints;
    codepoints.push_back(0x0401); // Ё
    for (uint32_t cp = 0x0410; cp <= 0x044F; ++cp) {
        codepoints.push_back(cp); // А..я
    }
    codepoints.push_back(0x0451); // ё
    // Extras
    codepoints.push_back(0x0406); codepoints.push_back(0x0456); // І, і
    codepoints.push_back(0x0407); codepoints.push_back(0x0457); // Ї, ї
    codepoints.push_back(0x0404); codepoints.push_back(0x0454); // Є, є
    codepoints.push_back(0x0490); codepoints.push_back(0x0491); // Ґ, ґ
    codepoints.push_back(0x040E); codepoints.push_back(0x045E); // Ў, ў
    // Punctuation
    codepoints.push_back(0x00AB); // «
    codepoints.push_back(0x00BB); // »
    codepoints.push_back(0x2014); // —
    codepoints.push_back(0x2013); // –
    codepoints.push_back(0x2026); // …
    codepoints.push_back(0x2116); // №
    codepoints.push_back(0x2022); // •

    // Create CoreText font
    // Note: PoB fontHeight is roughly cell height. We match fontSize ~ fontHeight * 0.78f
    CGFloat pointSize = (CGFloat)fontHeight * 0.78f;
    if (pointSize < 9.0) pointSize = 9.0;

    CTFontRef ctFont = CTFontCreateWithName((__bridge CFStringRef)fontFaceName, pointSize, nullptr);
    if (!ctFont) {
        ctFont = CTFontCreateWithName(CFSTR("Helvetica"), pointSize, nullptr);
    }

    // New atlas size: double height
    int newW = oldW;
    int newH = oldH * 2;
    std::vector<uint32_t> newPixels(newW * newH, 0x00FFFFFF); // White RGB, Alpha 0

    // Copy old pixels to top half
    for (int y = 0; y < oldH; ++y) {
        for (int x = 0; x < oldW; ++x) {
            newPixels[y * newW + x] = oldPixels[y * oldW + x];
        }
    }

    // Packing state in bottom half
    int curX = 1;
    int curY = oldH + 2;
    int rowH = fontHeight + 2;

    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();

    for (uint32_t cp : codepoints) {
        UniChar chs[2];
        int numChs = 0;
        if (cp <= 0xFFFF) {
            chs[0] = (UniChar)cp;
            numChs = 1;
        } else {
            chs[0] = (UniChar)(0xD800 + ((cp - 0x10000) >> 10));
            chs[1] = (UniChar)(0xDC00 + ((cp - 0x10000) & 0x3FF));
            numChs = 2;
        }

        CGGlyph glyphs[2];
        if (!CTFontGetGlyphsForCharacters(ctFont, chs, glyphs, numChs)) {
            continue;
        }

        CGSize advance;
        CTFontGetAdvancesForGlyphs(ctFont, kCTFontOrientationHorizontal, glyphs, &advance, 1);
        CGRect bbox;
        CTFontGetBoundingRectsForGlyphs(ctFont, kCTFontOrientationHorizontal, glyphs, &bbox, 1);

        int glyphW = (int)std::ceil(bbox.size.width);
        if (glyphW < 1) glyphW = 1;
        int cellW = glyphW + 2;

        if (curX + cellW >= newW - 1) {
            curX = 1;
            curY += rowH;
        }

        if (curY + fontHeight >= newH) {
            std::cerr << "Atlas overflow for " << tgaPath << "! Expanding further...\n";
            break;
        }

        // Render glyph into a temporary small buffer
        int renderW = glyphW + 4;
        int renderH = fontHeight;
        std::vector<uint32_t> tempBuf(renderW * renderH, 0);

        CGContextRef ctx = CGBitmapContextCreate(
            tempBuf.data(),
            renderW,
            renderH,
            8,
            renderW * 4,
            colorSpace,
            kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big
        );

        if (ctx) {
            CGContextSetAllowsAntialiasing(ctx, true);
            CGContextSetShouldAntialias(ctx, true);
            CGContextSetAllowsFontSmoothing(ctx, true);
            CGContextSetShouldSmoothFonts(ctx, true);

            // Clear to transparent black
            CGContextClearRect(ctx, CGRectMake(0, 0, renderW, renderH));

            // Set text color to white
            CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0);

            // Compute baseline offset: CoreGraphics is bottom-up, font baseline ~ descent
            CGFloat descent = CTFontGetDescent(ctFont);
            CGPoint textPos = CGPointMake(1.0 - bbox.origin.x, descent + 1.0);

            CTFontDrawGlyphs(ctFont, glyphs, &textPos, 1, ctx);
            CGContextRelease(ctx);
        }

        // Copy rendered glyph into atlas with format: RGB=(255, 255, 255), A=alpha
        int destX = curX;
        int destY = curY;

        for (int gy = 0; gy < renderH; ++gy) {
            // tempBuf is bottom-up from CoreGraphics, atlas is top-down
            int srcRow = renderH - 1 - gy;
            for (int gx = 0; gx < glyphW && (destX + gx) < newW; ++gx) {
                uint32_t px = tempBuf[srcRow * renderW + gx];
                // In BigEndian RGBA: px = (R << 24) | (G << 16) | (B << 8) | A
                uint8_t a = (uint8_t)(px & 0xFF);
                // SimpleGraphic BGRA: B=255, G=255, R=255, A=a
                uint32_t bgra = 0x00FFFFFF | ((uint32_t)a << 24);
                newPixels[(destY + gy) * newW + (destX + gx)] = bgra;
            }
        }

        int sl = (int)std::floor(bbox.origin.x);
        if (sl < 0) sl = 0;
        int sr = (int)std::ceil(advance.width) - glyphW - sl;
        if (sr < 0) sr = 0;

        AddedGlyph ag;
        ag.cp = cp;
        ag.x = destX;
        ag.y = destY;
        ag.w = glyphW;
        ag.sl = sl;
        ag.sr = sr;
        outGlyphs.push_back(ag);

        curX += cellW;
    }

    CGColorSpaceRelease(colorSpace);
    CFRelease(ctFont);

    // Save updated TGA
    if (!SaveTGA(tgaPath, newW, newH, newPixels)) {
        std::cerr << "Failed to save TGA: " << tgaPath << "\n";
        return false;
    }

    return true;
}

// Process an entire .tgf font definition and all its height .tga files
bool ProcessFont(const std::string& tgfPath) {
    std::cout << "Processing font: " << tgfPath << " ...\n";
    std::string baseNoExt = tgfPath.substr(0, tgfPath.rfind(".tgf"));
    std::string fontName = fs::path(baseNoExt).filename().string();
    NSString* fontFaceName = GetMacOSFontName(fontName);

    std::ifstream in(tgfPath);
    if (!in) {
        std::cerr << "Cannot open " << tgfPath << "\n";
        return false;
    }

    std::vector<std::string> lines;
    std::string line;
    while (std::getline(in, line)) {
        lines.push_back(line);
    }
    in.close();

    // Find sections HEIGHT <h>;
    std::vector<std::string> newLines;
    int currentH = 0;
    std::vector<AddedGlyph> glyphsForH;

    for (size_t i = 0; i < lines.size(); ++i) {
        const std::string& l = lines[i];
        int h = 0;
        if (sscanf(l.c_str(), "HEIGHT %d;", &h) == 1) {
            // If we had a previous height, flush its glyphs before starting new height
            if (currentH > 0 && !glyphsForH.empty()) {
                for (const auto& g : glyphsForH) {
                    char buf[128];
                    snprintf(buf, sizeof(buf), "GLYPH %u %u %u %u %d %d;\t// U+%04X",
                             g.cp, g.x, g.y, g.w, g.sl, g.sr, g.cp);
                    newLines.push_back(buf);
                }
                glyphsForH.clear();
            }

            currentH = h;
            newLines.push_back(l);

            // Process corresponding .tga
            std::string tgaPath = baseNoExt + "." + std::to_string(h) + ".tga";
            if (fs::exists(tgaPath)) {
                ProcessFontHeight(tgaPath, h, fontFaceName, glyphsForH);
            }
        } else if (l.find("// U+") != std::string::npos || (l.rfind("GLYPH", 0) == 0 && std::count(l.begin(), l.end(), ' ') >= 6)) {
            // Skip already generated Unicode glyphs to prevent duplicates if re-run
            continue;
        } else {
            newLines.push_back(l);
        }
    }

    // Flush last height glyphs
    if (currentH > 0 && !glyphsForH.empty()) {
        for (const auto& g : glyphsForH) {
            char buf[128];
            snprintf(buf, sizeof(buf), "GLYPH %u %u %u %u %d %d;\t// U+%04X",
                     g.cp, g.x, g.y, g.w, g.sl, g.sr, g.cp);
            newLines.push_back(buf);
        }
    }

    // Write updated .tgf
    std::ofstream out(tgfPath);
    for (const auto& nl : newLines) {
        out << nl << "\n";
    }

    std::cout << "Successfully updated " << fontName << " with Cyrillic glyphs!\n";
    return true;
}

int main(int argc, const char* argv[]) {
    @autoreleasepool {
        std::string fontsDir;
        if (argc > 1) {
            fontsDir = argv[1];
        } else {
            std::cerr << "Usage: fontgen <path_to_fonts_directory>\n";
            return 1;
        }

        std::cout << "=== Cyrillic Font Generator for SimpleGraphic Windows ===\n";
        std::cout << "Target Directory: " << fontsDir << "\n";

        for (const auto& entry : fs::directory_iterator(fontsDir)) {
            if (entry.path().extension() == ".tgf") {
                ProcessFont(entry.path().string());
            }
        }

        std::cout << "=== Font generation completed successfully! ===\n";
    }
    return 0;
}
