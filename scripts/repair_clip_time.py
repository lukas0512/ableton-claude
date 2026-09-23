"""Repair arrangement clips whose `Time` attribute disagrees with `CurrentStart`.

An earlier XML edit copied clips and moved CurrentStart/CurrentEnd without updating
Time, which Live uses to place the clip. Live then stacks the copy on top of the
original and lists "ghost" clips that its API cannot delete. Live itself always
writes Time == CurrentStart for arrangement clips, so this sets Time to CurrentStart.

Only run it with the Set closed in Live. It writes a timestamped backup first.

    python scripts/repair_clip_time.py "path/to/Set.als"          # dry run
    python scripts/repair_clip_time.py "path/to/Set.als" --write
"""
import gzip
import shutil
import sys
import time
import xml.etree.ElementTree as ET


def main(path, write):
    raw = gzip.open(path, "rb").read()
    root = ET.fromstring(raw)
    fixed = {}
    for tr in root.iter():
        if tr.tag not in ("AudioTrack", "MidiTrack"):
            continue
        name = tr.find(".//Name/EffectiveName").get("Value")
        for tag in ("AudioClip", "MidiClip"):
            for c in tr.iter(tag):
                cs = c.find("CurrentStart")
                if cs is None or c.get("Time") is None:
                    continue
                if abs(float(c.get("Time")) - float(cs.get("Value"))) > 1e-6:
                    c.set("Time", cs.get("Value"))
                    fixed[name] = fixed.get(name, 0) + 1
    for name, n in fixed.items():
        print("  %-40s %5d clips" % (name, n))
    print("total: %d clips on %d tracks" % (sum(fixed.values()), len(fixed)))
    if not write or not fixed:
        print("dry run: nothing written" if not write else "nothing to fix")
        return
    backup = path + ".bak-%s" % time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, backup)
    with gzip.open(path, "wb") as f:
        f.write(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    print("written; backup at", backup)


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv)
