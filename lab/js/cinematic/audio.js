// Browser-native sound design for the opening film, synthesized with the Web Audio API so no
// recorded assets are needed. Every cue is scheduled against film time; seeking reschedules.

export const CUES = [
  { t: 0.4, kind: "pencil", dur: 6.4 },
  { t: 7.2, kind: "rise", dur: 5.0 },
  { t: 15.3, kind: "clunk" },
  { t: 15.9, kind: "dim" },
  { t: 19.0, kind: "scan", dur: 8.0 },
  { t: 27.4, kind: "ping", n: 0 }, { t: 28.2, kind: "ping", n: 1 }, { t: 29.0, kind: "ping", n: 2 }, { t: 29.8, kind: "ping", n: 3 }, { t: 30.6, kind: "ping", n: 4 },
  { t: 31.5, kind: "whoosh", dur: 3.5 },
  { t: 37.2, kind: "type", dur: 2.2 },
  { t: 50.0, kind: "stop" },
  { t: 51.2, kind: "pop" },
  { t: 52.4, kind: "hum", dur: 3.5 },
  { t: 63.0, kind: "whoosh", dur: 3.0, reverse: true },
  { t: 68.0, kind: "chord", dur: 12 },
];

export class FilmAudio {
  constructor() {
    this.ctx = null;
    this.nodes = [];
    this.enabled = false;
    this.ambience = null;
  }

  async enable() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.8;
      const comp = this.ctx.createDynamicsCompressor();
      this.master.connect(comp).connect(this.ctx.destination);
      const len = this.ctx.sampleRate * 2;
      this.noise = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
      const d = this.noise.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    }
    if (this.ctx.state === "suspended") await this.ctx.resume();
    this.enabled = true;
    return true;
  }

  disable() { this.enabled = false; this.stopAll(); }

  stopAll() {
    for (const n of this.nodes) { try { n.stop?.(); n.disconnect?.(); } catch { /* already stopped */ } }
    this.nodes = [];
    this.ambience = null;
  }

  /** Schedule every cue after film time t, as if playback started now. */
  seek(t, playing) {
    this.stopAll();
    if (!this.enabled || !playing || !this.ctx) return;
    const now = this.ctx.currentTime + 0.05;
    this.startAmbience(now, t);
    for (const cue of CUES) {
      const end = cue.t + (cue.dur || 1);
      if (end < t) continue;
      const at = now + Math.max(cue.t - t, 0);
      const offset = Math.max(t - cue.t, 0);
      this[cue.kind]?.(at, cue, offset);
    }
  }

  track(node) { this.nodes.push(node); return node; }

  gain(value, at) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(value, at);
    g.connect(this.master);
    return g;
  }

  osc(type, freq, at, dur, out) {
    const o = this.track(this.ctx.createOscillator());
    o.type = type; o.frequency.setValueAtTime(freq, at);
    o.connect(out); o.start(at); o.stop(at + dur + 0.1);
    return o;
  }

  noiseSource(at, dur, out) {
    const s = this.track(this.ctx.createBufferSource());
    s.buffer = this.noise; s.loop = true;
    s.connect(out); s.start(at); s.stop(at + dur + 0.1);
    return s;
  }

  startAmbience(at, t) {
    if (t > 79) return;
    const remaining = 80 - t;
    const g = this.gain(0, at);
    g.gain.linearRampToValueAtTime(0.045, at + 1.5);
    if (t < 50 && remaining > 30) {
      g.gain.setValueAtTime(0.045, at + (50 - t));
      g.gain.linearRampToValueAtTime(0.0001, at + (50 - t) + 0.6);
      g.gain.linearRampToValueAtTime(0.04, at + (56 - t));
    }
    const lp = this.ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 420; lp.connect(g);
    for (const f of [55, 82.4, 110.3]) this.osc("triangle", f, at, remaining, lp);
  }

  pencil(at, cue, offset) {
    const dur = cue.dur - offset;
    if (dur <= 0) return;
    const bp = this.ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 3200; bp.Q.value = 0.9;
    const g = this.gain(0, at);
    bp.connect(g);
    this.noiseSource(at, dur, bp);
    for (let s = 0; s < dur; s += 0.18 + Math.random() * 0.22) {
      g.gain.setValueAtTime(0.0, at + s);
      g.gain.linearRampToValueAtTime(0.09 + Math.random() * 0.06, at + s + 0.04);
      g.gain.linearRampToValueAtTime(0.01, at + s + 0.16);
    }
  }

  rise(at, cue, offset) {
    const dur = cue.dur - offset; if (dur <= 0) return;
    const g = this.gain(0, at); g.gain.linearRampToValueAtTime(0.05, at + dur * 0.7); g.gain.linearRampToValueAtTime(0, at + dur);
    const o = this.osc("sine", 220, at, dur, g); o.frequency.exponentialRampToValueAtTime(440, at + dur);
  }

  clunk(at) {
    const g = this.gain(0.5, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.5);
    const lp = this.ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 500; lp.connect(g);
    this.noiseSource(at, 0.12, lp);
    const g2 = this.gain(0.4, at); g2.gain.exponentialRampToValueAtTime(0.001, at + 0.6);
    const o = this.osc("sine", 90, at, 0.6, g2); o.frequency.exponentialRampToValueAtTime(45, at + 0.5);
  }

  dim(at) {
    const g = this.gain(0.18, at); g.gain.exponentialRampToValueAtTime(0.001, at + 1.6);
    const o = this.osc("sine", 160, at, 1.6, g); o.frequency.exponentialRampToValueAtTime(38, at + 1.5);
  }

  scan(at, cue, offset) {
    const dur = cue.dur - offset; if (dur <= 0) return;
    const bp = this.ctx.createBiquadFilter(); bp.type = "bandpass"; bp.Q.value = 6;
    bp.frequency.setValueAtTime(300 + 2100 * (offset / cue.dur), at); bp.frequency.linearRampToValueAtTime(2400, at + dur);
    const g = this.gain(0, at); g.gain.linearRampToValueAtTime(0.06, at + 0.6); g.gain.setValueAtTime(0.06, at + dur - 0.8); g.gain.linearRampToValueAtTime(0, at + dur);
    bp.connect(g);
    this.osc("sawtooth", 110, at, dur, bp);
    this.osc("sawtooth", 110.7, at, dur, bp);
  }

  ping(at, cue) {
    const notes = [880, 987.8, 1174.7, 1318.5, 1480];
    const g = this.gain(0.08, at); g.gain.exponentialRampToValueAtTime(0.0008, at + 1.4);
    this.osc("sine", notes[cue.n % notes.length], at, 1.4, g);
  }

  whoosh(at, cue, offset) {
    const dur = cue.dur - offset; if (dur <= 0) return;
    const bp = this.ctx.createBiquadFilter(); bp.type = "bandpass"; bp.Q.value = 1.2;
    const [f0, f1] = cue.reverse ? [2400, 280] : [280, 2400];
    bp.frequency.setValueAtTime(f0, at); bp.frequency.exponentialRampToValueAtTime(f1, at + dur);
    const g = this.gain(0, at); g.gain.linearRampToValueAtTime(0.16, at + dur * 0.5); g.gain.linearRampToValueAtTime(0, at + dur);
    bp.connect(g);
    this.noiseSource(at, dur, bp);
  }

  type(at, cue, offset) {
    const dur = cue.dur - offset;
    for (let s = 0; s < dur; s += 0.09) {
      const g = this.gain(0.05, at + s); g.gain.exponentialRampToValueAtTime(0.0005, at + s + 0.05);
      const hp = this.ctx.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 2500; hp.connect(g);
      this.noiseSource(at + s, 0.04, hp);
    }
  }

  stop(at) {
    const g = this.gain(0.12, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.8);
    const o = this.osc("sawtooth", 220, at, 0.8, g); o.frequency.exponentialRampToValueAtTime(30, at + 0.75);
  }

  pop(at) {
    const g = this.gain(0.2, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.25);
    const o = this.osc("sine", 520, at, 0.25, g); o.frequency.exponentialRampToValueAtTime(980, at + 0.08);
  }

  hum(at, cue, offset) {
    const dur = cue.dur - offset; if (dur <= 0) return;
    const g = this.gain(0, at); g.gain.linearRampToValueAtTime(0.05, at + 0.8); g.gain.linearRampToValueAtTime(0, at + dur);
    this.osc("sine", 220, at, dur, g); this.osc("sine", 330, at, dur, g);
  }

  chord(at, cue, offset) {
    const dur = cue.dur - offset; if (dur <= 0) return;
    const g = this.gain(0, at); g.gain.linearRampToValueAtTime(0.07, at + 2.5); g.gain.setValueAtTime(0.07, at + dur - 3); g.gain.linearRampToValueAtTime(0, at + dur);
    const lp = this.ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 1800; lp.connect(g);
    for (const f of [110, 164.8, 220, 277.2, 329.6]) { this.osc("sine", f, at, dur, lp); this.osc("triangle", f * 1.003, at, dur, lp); }
  }
}
