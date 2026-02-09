#!/usr/bin/env python3
import codecs

BOMS = [
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
    (codecs.BOM_UTF8, "utf-8-sig"),
]

WRITE_ENCODINGS = {
    "utf-32": "utf-32",
    "utf-16": "utf-16",
    "utf-8-sig": "utf-8-sig",
}

FALLBACK_ENCODINGS = ["utf-8", "cp1252", "latin-1"]

def detect_encoding(path):
    with open(path, "rb") as f:
        raw = f.read(4)
    for bom, enc in BOMS:
        if raw.startswith(bom):
            return enc
    return None

def read_with_encoding(path):
    bom_enc = detect_encoding(path)
    if bom_enc:
        with open(path, "r", encoding=bom_enc) as f:
            content = f.read()
        if content and content[0] == '\ufeff':
            content = content[1:]
        return content, bom_enc
    
    with open(path, "rb") as f:
        raw = f.read()
    
    for enc in FALLBACK_ENCODINGS:
        try:
            content = raw.decode(enc)
            if content and content[0] == '\ufeff':
                content = content[1:]
            return content, enc
        except (UnicodeDecodeError, LookupError):
            continue
    
    return raw.decode("latin-1", errors="replace"), "latin-1"

def read_lines_with_encoding(path):
    content, encoding = read_with_encoding(path)
    lines = content.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        pass
    return lines, encoding

def write_with_encoding(path, content, encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="") as f:
        f.write(content)

def write_lines_with_encoding(path, lines, encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="") as f:
        f.writelines(lines)
