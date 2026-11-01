"""Lay out the tutorial film: scenes, narration cues, visual events and sound cues.

One source of truth for the picture, the sound and the captions. Reads the
narration durations (build/tutorial/narration/durations.json) and, when
present, word timings (words.json) so beats land on the right word.

    python tools/tutorial/timeline.py

Writes assets/tutorial/timeline.js, the caption and chapter files in
assets/tutorial/, and build/tutorial/timeline.json for the audio builder.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NARR = ROOT / "build" / "tutorial" / "narration"
ASSETS = ROOT / "assets" / "tutorial"
SCRIPT = json.loads((ROOT / "tools" / "tutorial" / "narration.json").read_text(encoding="utf-8"))
TEXT = {line["id"]: line["text"] for line in SCRIPT["lines"]}
DUR = json.loads((NARR / "durations.json").read_text())
WORDS = json.loads((NARR / "words.json").read_text()) if (NARR / "words.json").exists() else {}
FPS = 24


def snap(t):
    """Events land on a drawing: 12 drawings per second, on twos."""
    return round(round(t * 12) / 12, 4)


class Cut:
    def __init__(self, name, width, height):
        self.name, self.width, self.height = name, width, height
        self.scenes, self.cues, self.events, self.sfx = [], [], {}, []

    def scene(self, sid, start, end, chapter=None, commands=None):
        self.scenes.append({"id": sid, "start": snap(start), "end": snap(end),
                            "chapter": chapter, "commands": commands})

    def say(self, cid, at):
        at = snap(at)
        end = round(at + DUR[cid], 3)
        if self.cues and at < self.cues[-1]["end"] + 0.15:
            raise SystemExit(f"{self.name}: {cid} at {at} overlaps {self.cues[-1]['id']} ending {self.cues[-1]['end']}")
        self.cues.append({"id": cid, "start": at, "end": end, "text": TEXT[cid]})
        self.events[cid] = at
        self.events[cid + ".end"] = end
        return end

    def word(self, cid, word, which=0, edge="start"):
        """Absolute time of a word inside a spoken line (falls back to an even split)."""
        start = self.events[cid]
        words = WORDS.get(cid)
        if words:
            hits = [w for w in words if w["w"].strip(".,!?;:…\"'").lower() == word.lower()]
            if len(hits) > which:
                return round(start + hits[which][edge], 3)
        parts = TEXT[cid].split()
        idx = [i for i, p in enumerate(parts) if p.strip(".,!?;:…\"'").lower() == word.lower()]
        frac = (idx[which] / len(parts)) if len(idx) > which else 0.5
        return round(start + frac * DUR[cid], 3)

    def ev(self, name, t, sound=None, **params):
        t = snap(t)
        if name in self.events:
            raise SystemExit(f"duplicate event {name}")
        self.events[name] = t
        if sound:
            self.sfx.append({"t": t, "kind": sound, **params})
        return t

    def sound(self, t, kind, **params):
        self.sfx.append({"t": snap(t), "kind": kind, **params})

    def duration(self):
        return max(s["end"] for s in self.scenes)

    def data(self):
        return {"name": self.name, "width": self.width, "height": self.height, "fps": FPS,
                "duration": self.duration(), "scenes": self.scenes, "cues": self.cues,
                "events": dict(sorted(self.events.items(), key=lambda kv: kv[1])), "sfx": sorted(self.sfx, key=lambda s: s["t"])}


def main_cut():
    c = Cut("main", 1920, 1080)
    # SCENE 1 — cover and scope
    c.ev("s1.lampOn", 0.75, "lamp")
    c.ev("s1.slide0", 1.25, "felt", dur=2.4)
    c.ev("s1.slide1", 3.75)
    c.say("s1a", 1.5)
    c.ev("s1.cut", 4.25)
    c.say("s1b", 4.75)
    c.ev("s1.reach", 7.25)
    c.ev("s1.rings", 8.0, "rings")
    c.ev("s1.coverOpen", 8.0, "page", soft=1)
    c.ev("s1.coverOpened", 9.0)
    c.say("s1c", 9.5)
    hit = c.word("s1c", "flight") + 0.05
    c.ev("s1.stampDown", hit - 0.75)
    c.ev("s1.stampHit", hit, "stamp")
    c.ev("s1.stampUp", hit + 0.6)
    c.ev("s1.turn", 18.25, "page")
    c.scene("cover", 0, 19.0, "Cover and scope", "cover")

    # SCENE 2 — table of contents
    for i in range(9):
        c.ev(f"s2.lead{i}", 19.5 + i * 0.5, "pencil")
    c.say("s2a", 23.75)
    c.ev("s2.circle6", c.word("s2a", "not") - 0.1, "scribble")
    c.say("s2b", 26.5)
    c.ev("s2.circle8", c.word("s2b", "not") - 0.1, "scribble")
    c.say("s2c", 29.0)
    c.ev("s2.underline7", c.word("s2c", "status") - 0.2, "pencil")
    c.ev("s2.turn", 31.75, "page")
    c.scene("toc", 19.0, 32.5, "Table of contents", "toc")

    # SCENE 3 — Section I, description
    c.ev("s3.turnFig", 34.75, "page")
    c.say("s3a", 35.75)
    c.ev("s3.explode", 36.5, "squish")
    for i in range(8):
        c.ev(f"s3.callout{i}", 38.25 + i * 0.58, "pen")
    c.ev("s3.unfold", 43.75, "unfold")
    c.say("s3b", 45.0)
    c.ev("s3.wifi", c.word("s3b", "launcher") - 0.3)
    c.say("s3c", 48.25)
    c.ev("s3.uart", c.word("s3c", "rocket") - 0.3)
    c.say("s3d", 51.75)
    c.ev("s3.internals", c.word("s3d", "motion"))
    c.ev("s3.canards", c.word("s3d", "canards") - 0.4, "whir", n=2)
    c.ev("s3.viewAA", 58.0, "card")
    c.say("s3e", 58.75)
    c.ev("s3.roll", 58.75)
    c.ev("s3.steady", c.word("s3e", "roll"), "whir", n=3)
    c.say("s3f", 61.5)
    c.ev("s3.turn", 64.25, "page")
    c.scene("desc", 32.5, 65.0, "Section I · Description", "desc")

    # SCENE 4 — II-A offline review
    c.ev("s4.turn0", 67.5, "page")
    c.ev("s4.push", 68.25, "felt", dur=1.0)
    c.say("s4a", 68.75)
    c.say("s4b", 71.75)
    c.say("s4c", 75.0)
    c.ev("s4.tick1", c.word("s4c", "newer") + 0.2, "tick")
    t = c.ev("s4.type2", c.word("s4c", "status") - 0.15, "keys", n=25, dur=0.8)
    c.ev("s4.out2", t + 0.95)
    c.ev("s4.tick2", t + 1.15, "tick")
    t = c.ev("s4.type3", c.word("s4c", "check") - 0.15, "keys", n=24, dur=0.75)
    c.ev("s4.tick3", t + 1.0, "tick")
    c.say("s4d", 79.25)
    t = c.ev("s4.type4", 79.33, "keys", n=46, dur=1.25)
    c.ev("s4.tick4", t + 1.4, "tick")
    t = c.ev("s4.type5", c.word("s4d", "verify") - 0.1, "keys", n=38, dur=1.0)
    c.ev("s4.tick5", t + 1.15, "tick")
    c.ev("s4.booklet", c.word("s4d", "browser") - 0.2, "paper")
    c.ev("s4.tick6", c.events["s4d.end"] + 0.25, "tick")
    c.say("s4e", 84.0)
    c.ev("s4.note", 84.0)
    c.ev("s4.turn", 89.0, "page")
    c.scene("offline", 65.0, 89.75, "Section II-A · Offline review", "offline")

    # SCENE 5 — II-B inert bench preflight
    c.ev("s5.warning", 90.25, "thunk")
    c.say("s5a", 90.5)
    c.ev("s5.hornLift", c.word("s5a", "servo") - 0.2)
    c.ev("s5.hornDish", c.word("s5a", "disconnected") + 0.3, "clink")
    c.ev("s5.tick0", c.word("s5a", "energetic") + 0.1, "tick")
    c.ev("s5.caution", 97.0, "thunk")
    c.say("s5b", 97.5)
    c.say("s5c", 101.25)
    c.ev("s5.tick1", c.word("s5c", "verified") + 0.3, "tick")
    c.ev("s5.tick2", c.events["s5c.end"] + 0.1, "tick")
    c.ev("s5.wifi", 105.25)
    c.ev("s5.tick3", 105.75, "tick")
    c.say("s5d", 106.25)
    c.ev("s5.dashOn", c.word("s5d", "open") - 0.1, "click")
    c.ev("s5.tick4", c.word("s5d", "open") + 0.5, "tick")
    c.ev("s5.rawGlow", c.word("s5d", "raw"))
    c.ev("s5.tick4s", c.events["s5d.end"] - 0.3, "tick")
    c.ev("s5.telemetry", c.events["s5d.end"] + 0.1)
    c.ev("s5.tick5", c.events["s5d.end"] + 0.6, "tick")
    c.say("s5e", 111.25)
    c.ev("s5.armOn", c.word("s5e", "on") - 0.1, "toggle")
    c.ev("s5.ready", c.word("s5e", "ready"), "beep")
    c.ev("s5.tick6", c.events["s5e.end"] + 0.2, "tick")
    c.say("s5f", 114.5)
    c.ev("s5.armOff", c.word("s5f", "off") - 0.1, "toggle")
    c.ev("s5.abort", c.word("s5f", "safe") - 0.1, "buzz")
    c.ev("s5.tick7", c.events["s5f.end"] + 0.2, "tick")
    c.ev("s5.note8", 118.6)
    c.ev("s5.calibrate", 119.0, "click")
    c.ev("s5.tick8", 119.85, "tick")
    c.say("s5g", 120.5)
    c.ev("s5.reach", 120.6)
    c.ev("s5.press", c.events["s5g.end"] - 0.15, "click")
    c.ev("s5.slip", c.events["s5g.end"] + 0.2, "slip")
    c.say("s5h", 123.5)
    c.ev("s5.nod", c.events["s5h.end"] + 0.25)
    c.say("s5i", 125.25)
    c.ev("s5.tick9", c.events["s5i.end"] + 0.35, "tick")
    c.ev("s5.tick10", 127.5, "tick")
    c.ev("s5.lid", 127.75, "lid")
    c.ev("s5.turn", 128.5, "page")
    c.scene("preflight", 89.75, 129.25, "Section II-B · Inert bench preflight", "preflight")

    # SCENE 6 — II-C canards and gain windows
    c.say("s6a", 130.0)
    for i in range(4):
        c.ev(f"s6.center{i}", 130.5 + i * 1.0, "whir", n=1)
    c.say("s6b", 135.75)
    c.ev("s6.hold", c.word("s6b", "still") - 0.3)
    c.ev("s6.calibrate", c.word("s6b", "calibrate") + 0.1, "click")
    c.ev("s6.card", c.events["s6b.end"] + 0.25, "card")
    c.say("s6c", 142.75)
    for i in range(4):
        c.ev(f"s6.rock{i}", 143.5 + i * 1.2, "whir", n=2)
        c.ev(f"s6.row{i}", 144.3 + i * 1.2, "tick")
    c.ev("s6.turn", 149.0, "page")
    c.scene("canards", 129.25, 149.75, "Section II-C · Canards and gain windows", "canards")

    # SCENE 7 — II-D session passport
    c.say("s7a", 150.25)
    c.ev("s7.box", c.word("s7a", "cleanly") - 0.2, "lid")
    c.ev("s7.tick1", c.word("s7a", "cleanly") + 0.3, "tick")
    c.ev("s7.declare", c.word("s7a", "declare"), "scribble")
    c.ev("s7.tick2", c.word("s7a", "did") + 0.2, "tick")
    c.ev("s7.passport", c.word("s7a", "passport") - 0.2, "stampSmall")
    c.ev("s7.tick34", c.events["s7a.end"] + 0.2, "tick")
    c.say("s7b", 155.0)
    c.ev("s7.hover", 155.0)
    c.ev("s7.tag", c.word("s7b", "named"), "felt", dur=0.6)
    c.say("s7c", 158.0)
    c.ev("s7.noFall", c.word("s7c", "accept") - 0.1)
    c.ev("s7.turn", 163.5, "page")
    c.scene("passport", 149.75, 164.25, "Section II-D · Session passport", "passport")

    # SCENE 8 — Sections III and IV, abnormal operations
    c.ev("s8.turn0", 167.0, "page")
    c.ev("s8.slack", 167.75, "squish", soft=1)
    c.ev("s8.tile", 168.5, "chime")
    c.say("s8a", 168.75)
    c.ev("s8.board", c.word("s8a", "board") - 0.4, "card")
    c.ev("s8.tick1", c.word("s8a", "board") + 0.3, "tick")
    c.ev("s8.dump", c.events["s8a.end"] - 0.25, "click")
    c.ev("s8.tick2", c.events["s8a.end"] + 0.3, "tick")
    c.say("s8b", 175.75)
    c.ev("s8.reply", 176.0, "plinks", n=3)
    c.ev("s8.update", c.word("s8b", "clears"), "chime", soft=1)
    c.ev("s8.tick3", c.word("s8b", "sensor") + 0.2, "tick")
    c.say("s8c", 181.25)
    c.ev("s8.silence", 181.25)
    c.ev("s8.tree", 184.0, "page", soft=1)
    for i in range(6):
        c.ev(f"s8.row{i}", 184.75 + i * 0.42, "plink")
    c.say("s8d", 187.5)
    c.ev("s8.turn", 189.75, "page")
    c.scene("abnormal", 164.25, 190.5, "Sections III and IV · Abnormal operations", "abnormal")

    # SCENE 9 — Section V, operating limitations
    c.ev("s9.turn0", 193.25, "page")
    c.say("s9a", 194.0)
    c.ev("s9.pan", 195.0)
    c.say("s9b", 195.75)
    c.ev("s9.linkage", 196.0)
    c.ev("s9.gap", c.word("s9b", "close") - 0.1, "thunk", soft=1)
    c.say("s9c", 200.75)
    c.ev("s9.gauge", 201.0)
    c.ev("s9.needle", c.word("s9c", "twenty") + 0.2, "tick")
    c.say("s9d", 205.75)
    c.ev("s9.scales", 205.75, "clink")
    c.say("s9e", 208.25)
    c.ev("s9.sticky", 208.25)
    c.ev("s9.stamp", c.word("s9e", "one") - 0.05, "stamp")
    c.ev("s9.back", c.events["s9e.end"] + 0.4)
    c.say("s9f", 212.5)
    c.ev("s9.turn", 217.25, "page")
    c.scene("limits", 190.5, 218.0, "Section V · Operating limitations", "limits")

    # SCENE 10 — change data summary, invitation, end card
    c.say("s10a", 218.75)
    for i in range(8):
        c.ev(f"s10.bead{i}", 219.0 + i * 0.3, "plink")
    c.ev("s10.tag", c.word("s10a", "person") - 0.3, "felt", dur=0.5)
    c.ev("s10.close", 225.0)
    c.ev("s10.rings", 225.75, "rings")
    c.ev("s10.coverShut", 226.25, "thunk", soft=1)
    c.ev("s10.cut", 226.75)
    c.say("s10b", 227.5)
    c.ev("s10.lampOff", c.events["s10b.end"] + 1.0, "lamp")
    c.say("s10c", c.events["s10b.end"] + 2.25)
    c.ev("s10.endHold", c.events["s10c.end"] + 3.75)
    c.scene("gates", 218.0, 226.75, "Change data summary", "gates")
    c.scene("end", 226.75, snap(c.events["s10c.end"] + 3.75), "Run the review", "gates")
    credits = c.scenes[-1]["end"]
    c.ev("cr.index", credits + 4.0, "page", soft=1)
    c.ev("cr.disclaimer", credits + 6.75, "page", soft=1)
    c.scene("credits", credits, credits + 9.75, "Glossary, index and disclaimer", "gates")
    return c


def vertical_cut():
    c = Cut("preflight60", 1080, 1920)
    c.ev("v.lampOn", 0.25, "lamp")
    c.ev("v.toc", 3.0, "page")
    for i in range(9):
        c.ev(f"v.lead{i}", 3.5 + i * 0.12)
    c.say("s2a", 4.5)
    c.ev("v.circle6", c.word("s2a", "not") - 0.1, "scribble")
    c.say("s2b", 7.25)
    c.ev("v.circle8", c.word("s2b", "not") - 0.1, "scribble")
    c.say("s2c", 9.75)
    c.ev("v.turn", 12.5, "page")
    c.ev("v.warning", 13.75, "thunk")
    c.say("s5a", 14.0)
    c.ev("v.hornLift", c.word("s5a", "servo") - 0.2)
    c.ev("v.hornDish", c.word("s5a", "disconnected") + 0.3, "clink")
    c.ev("v.tick0", c.word("s5a", "energetic") + 0.1, "tick")
    c.ev("v.caution", 20.5, "thunk")
    c.say("s5b", 20.75)
    c.say("s5c", 24.5)
    c.ev("v.tick1", c.word("s5c", "verified") + 0.3, "tick")
    c.ev("v.tick2", c.events["s5c.end"] + 0.05, "tick")
    c.ev("v.tick3", c.events["s5c.end"] + 0.4, "tick")
    c.say("s5d", 28.75)
    c.ev("v.dashOn", c.word("s5d", "open") - 0.1, "click")
    c.ev("v.tick4", c.word("s5d", "open") + 0.5, "tick")
    c.ev("v.rawGlow", c.word("s5d", "raw"))
    c.ev("v.tick5", c.events["s5d.end"] + 0.2, "tick")
    c.say("s5e", 33.5)
    c.ev("v.armOn", c.word("s5e", "on") - 0.1, "toggle")
    c.ev("v.ready", c.word("s5e", "ready"), "beep")
    c.ev("v.tick6", c.events["s5e.end"] + 0.2, "tick")
    c.say("s5f", 36.5)
    c.ev("v.armOff", c.word("s5f", "off") - 0.1, "toggle")
    c.ev("v.abort", c.word("s5f", "safe") - 0.1, "buzz")
    c.ev("v.tick7", c.events["s5f.end"] + 0.1, "tick")
    c.ev("v.tick8", c.events["s5f.end"] + 0.5, "tick")
    c.say("s5g", 40.75)
    c.ev("v.reach", 40.75)
    c.ev("v.press", c.events["s5g.end"] - 0.15, "click")
    c.ev("v.slip", c.events["s5g.end"] + 0.2, "slip")
    c.say("s5h", 43.75)
    c.ev("v.nod", c.events["s5h.end"] + 0.25)
    c.say("s5i", 45.5)
    c.ev("v.tick9", c.events["s5i.end"] + 0.35, "tick")
    c.ev("v.end", 47.25, "page")
    c.say("s10c", 49.0)
    c.scene("vcover", 0, 3.0, "Preflight in 60 seconds", "cover")
    c.scene("vtoc", 3.0, 13.25, "Table of contents", "toc")
    c.scene("vpreflight", 13.25, 47.75, "Inert bench preflight", "preflight")
    c.scene("vend", 47.75, 58.0, "Run the review", "gates")
    return c


def ts(t, sep="."):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", sep)


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def write_captions(cut, stem):
    vtt = ["WEBVTT", "", "NOTE Captions for the Project 33 claymation tutorial (V3D-TO-33-1). Generated by tools/tutorial/timeline.py.", ""]
    srt = []
    for i, cue in enumerate(cut.cues, 1):
        end = cue["end"] + 0.25
        nxt = cut.cues[i]["start"] if i < len(cut.cues) else end
        end = min(end, nxt - 0.05)
        vtt += [f"{i}", f"{ts(cue['start'])} --> {ts(end)}", cue["text"], ""]
        srt += [f"{i}", f"{ts(cue['start'], ',')} --> {ts(end, ',')}", cue["text"], ""]
    (ASSETS / f"{stem}.en.vtt").write_text("\n".join(vtt), encoding="utf-8")
    (ASSETS / f"{stem}.en.srt").write_text("\n".join(srt), encoding="utf-8")


def write_chapters(cut, stem):
    chapters = []
    for s in cut.scenes:
        if s["chapter"] and (not chapters or chapters[-1]["title"] != s["chapter"]):
            chapters.append({"title": s["chapter"], "start": s["start"], "end": s["end"]})
        elif chapters:
            chapters[-1]["end"] = s["end"]
    vtt = ["WEBVTT", ""]
    for i, ch in enumerate(chapters, 1):
        vtt += [f"chapter-{i}", f"{ts(ch['start'])} --> {ts(ch['end'])}", ch["title"], ""]
    (ASSETS / f"{stem}.chapters.vtt").write_text("\n".join(vtt), encoding="utf-8")
    lines = [f"{mmss(ch['start'])} {ch['title']}" for ch in chapters]
    (ASSETS / f"{stem}.chapters.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return chapters


def main():
    main, vert = main_cut(), vertical_cut()
    write_captions(main, "tutorial")
    write_captions(vert, "preflight60")
    chapters = {"main": write_chapters(main, "tutorial"), "preflight60": write_chapters(vert, "preflight60")}
    data = {"main": main.data(), "preflight60": vert.data()}
    for key, cut in data.items():
        cut["chapters"] = chapters[key]
    build = ROOT / "build" / "tutorial"
    build.mkdir(parents=True, exist_ok=True)
    (build / "timeline.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    js = ("/* Generated by tools/tutorial/timeline.py. Do not edit by hand. */\n"
          "window.P33T_TIMELINE = " + json.dumps(data, separators=(",", ":")) + ";\n")
    (ASSETS / "timeline.js").write_text(js, encoding="utf-8")
    for cut in (main, vert):
        speech = sum(c["end"] - c["start"] for c in cut.cues)
        print(f"{cut.name}: {cut.duration():.2f}s ({mmss(cut.duration())}), {len(cut.cues)} cues, {speech:.1f}s speech, {len(cut.sfx)} sounds")


if __name__ == "__main__":
    main()
