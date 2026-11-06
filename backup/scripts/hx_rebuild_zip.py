#!/usr/bin/env python3
"""Rebuild download/henhaoxue-full-site.zip from the completed mirror."""
import hashlib
import zipfile
from pathlib import Path

SRC = Path("/home/z/my-project/henhaoxue-site")
OUT = Path("/home/z/my-project/download/henhaoxue-full-site.zip")

files = sorted(p for p in SRC.rglob("*") if p.is_file())
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in files:
        z.write(p, "henhaoxue-site/" + p.relative_to(SRC).as_posix())
    dirs = sorted({"henhaoxue-site/" + p.relative_to(SRC).as_posix() + "/"
                   for p in SRC.rglob("*") if p.is_dir()})
    for d in dirs:
        z.writestr(d, "")

print("written:", len(files), "files,", f"{OUT.stat().st_size/1048576:.1f} MB")

z = zipfile.ZipFile(OUT)
names = z.namelist()
assert z.testzip() is None
print("zip entries:", len(names),
      "| phrase-images:", sum(1 for x in names if "phrase-images" in x and not x.endswith("/")),
      "| reading-scenes:", sum(1 for x in names if "reading-scenes" in x and not x.endswith("/")),
      "| mp3:", sum(1 for x in names if ".mp3" in x))

spot = "henhaoxue-site/learning/phrase-images/001-46fe466291c4.webp"
ok = hashlib.sha1(z.read(spot)).hexdigest() == hashlib.sha1(
    (SRC / "learning/phrase-images/001-46fe466291c4.webp").read_bytes()).hexdigest()
print("spot-check sha equal:", ok)
