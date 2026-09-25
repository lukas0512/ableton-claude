"""A minimal Standard MIDI File writer (type 1), so heard parts can be opened anywhere."""
import struct

PPQ = 480


def _vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def _track(events):
    data = b""
    last = 0
    for tick, ev in sorted(events, key=lambda e: (e[0], e[1][0] & 0xF0 == 0x90)):
        data += _vlq(tick - last) + ev
        last = tick
    data += _vlq(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + data


def write(path, parts, bpm):
    """parts: [(name, channel, [[pitch, start_beat, dur_beats, velocity], ...]), ...]."""
    tempo = int(round(60_000_000 / bpm))
    tracks = [_track([(0, b"\xff\x51\x03" + tempo.to_bytes(3, "big")),
                      (0, b"\xff\x58\x04\x04\x02\x18\x08")])]
    for name, ch, notes in parts:
        ev = [(0, b"\xff\x03" + _vlq(len(name.encode())) + name.encode())]
        for p, s, d, v in notes:
            a = max(0, int(round(s * PPQ)))
            b = max(a + 1, int(round((s + d) * PPQ)))
            ev.append((a, bytes([0x90 | ch, int(p) & 0x7F, max(1, min(127, int(v)))])))
            ev.append((b, bytes([0x80 | ch, int(p) & 0x7F, 0])))
        tracks.append(_track(ev))
    head = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), PPQ)
    with open(path, "wb") as f:
        f.write(head + b"".join(tracks))
    return path


def read_notes(path):
    """[(track_name, [[pitch, start_beat, dur_beats, velocity], ...])] from a MIDI file
    (enough of the format to read sample-pack MIDI and our own files)."""
    data = open(path, "rb").read()
    if data[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    _, fmt, ntrk, div = struct.unpack(">IHHH", data[4:14])
    ppq = div if not div & 0x8000 else 480
    pos, out = 14, []
    for _ in range(ntrk):
        if data[pos:pos + 4] != b"MTrk":
            break
        ln = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        chunk, pos = data[pos + 8:pos + 8 + ln], pos + 8 + ln
        i, tick, status, name, on, notes = 0, 0, 0, "", {}, []
        while i < len(chunk):
            d = 0
            while True:
                c = chunk[i]
                i += 1
                d = (d << 7) | (c & 0x7F)
                if not c & 0x80:
                    break
            tick += d
            b0 = chunk[i]
            if b0 == 0xFF:
                typ, i = chunk[i + 1], i + 2
                ln2 = 0
                while True:
                    c = chunk[i]
                    i += 1
                    ln2 = (ln2 << 7) | (c & 0x7F)
                    if not c & 0x80:
                        break
                if typ == 0x03:
                    name = chunk[i:i + ln2].decode("latin-1", "replace")
                i += ln2
                continue
            if b0 in (0xF0, 0xF7):
                ln2 = 0
                i += 1
                while True:
                    c = chunk[i]
                    i += 1
                    ln2 = (ln2 << 7) | (c & 0x7F)
                    if not c & 0x80:
                        break
                i += ln2
                continue
            if b0 & 0x80:
                status, i = b0, i + 1
            kind = status & 0xF0
            n_data = 1 if kind in (0xC0, 0xD0) else 2
            args = chunk[i:i + n_data]
            i += n_data
            if kind == 0x90 and args[1] > 0:
                on[args[0]] = (tick, args[1])
            elif kind == 0x80 or (kind == 0x90 and args[1] == 0):
                if args[0] in on:
                    t0, v = on.pop(args[0])
                    notes.append([args[0], t0 / ppq, max(1, tick - t0) / ppq, v])
        if notes:
            out.append((name, sorted(notes, key=lambda n: (n[1], n[0]))))
    return out
