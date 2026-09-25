"""Write a heard groove as a Live groove file (.agr).

A Live groove is a MIDI clip whose notes' timing and velocity define the feel, plus
Timing / Random / Velocity / Quantize amounts. Live's own "Swing 16ths 59" file is the
template: its notes are replaced by one bar of 16ths placed where the reference's
hits land (median offset per step) with its accents, so the Groove Pool can put a
reference's swing and push on any clip.
"""
import os
import re

CORE_GROOVE = ("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/"
               "Grooves/Swing/Basic/Swing 16ths 59.agr")
USER_GROOVES = os.path.expanduser("~/Music/Ableton/User Library/Grooves/Claude")


def notes_from_template(template, period_s):
    """template: 16 dicts with offset_ms / accent_db (drums._timing). -> [(time_beats, velocity)]."""
    out = []
    accents = [t["accent_db"] for t in template if t.get("accent_db") is not None]
    top = max(accents) if accents else 0.0
    for t in template:
        off = t.get("offset_ms") or 0.0
        acc = t.get("accent_db")
        vel = 100.0 if acc is None else max(1.0, min(127.0, 127.0 + (acc - top) * 3.0))
        out.append((t["step"] / 4.0 + off / 1000.0 / period_s, vel))
    return out


def write(name, notes, out_dir=USER_GROOVES, template_path=CORE_GROOVE, timing=100, velocity=30):
    """Write <out_dir>/<name>.agr; notes: [(time_beats, velocity)] within one bar (4 beats)."""
    xml = open(template_path, encoding="utf-8").read()
    ev = "\n".join(
        '\t\t\t\t\t\t\t\t\t<MidiNoteEvent Time="%.6f" Duration="0.0625" Velocity="%.4f" '
        'OffVelocity="64" IsEnabled="true" NoteId="%d" />' % (max(0.0, t), v, i + 1)
        for i, (t, v) in enumerate(sorted(notes)))
    xml, n = re.subn(r"(<KeyTrack Id=\"\d+\">\s*<Notes>).*?(</Notes>)", r"\1\n" + ev.replace("\\", "\\\\") + r"\n\t\t\t\t\t\t\t\t\2",
                     xml, count=1, flags=re.S)
    if n != 1:
        raise ValueError("template has no note block")
    for tag in ("CurrentEnd", "LoopEnd", "OutMarker", "HiddenLoopEnd"):
        xml = re.sub(r'<%s Value="[^"]*" />' % tag, '<%s Value="4" />' % tag, xml, count=1)
    xml = re.sub(r'(<NextId Value=")\d+(" />)', r"\g<1>%d\2" % (len(notes) + 1), xml, count=1)
    xml = re.sub(r'<Name Value="[^"]*" />', '<Name Value="%s" />' % _esc(name), xml)
    xml = re.sub(r'<TimingAmount Value="[^"]*" />', '<TimingAmount Value="%d" />' % timing, xml, count=1)
    xml = re.sub(r'<VelocityAmount Value="[^"]*" />', '<VelocityAmount Value="%d" />' % velocity, xml, count=1)
    xml = re.sub(r"\s*<SourceContext>.*</SourceContext>", "", xml, flags=re.S)   # no stale browser path
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, _safe(name) + ".agr")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    return path


def _esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _safe(s):
    return re.sub(r"[^\w\-. ]+", "_", s).strip()[:80]
