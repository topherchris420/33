import { createValidityModel } from './validity.js';
import { flightState } from './symbology.js';

// A synthetic signal source and its observed state are deliberately distinct.
const sampleFor = (id, s) => ({
  airdata: { speed: s.speed, altitude: s.altitude, vs: s.vs },
  inertial: { pitch: s.pitch, roll: s.roll, heading: s.heading },
  gnss: { routeProgress: s.routeProgress },
})[id];

export function createDisplayStore({ motion = true } = {}) {
  const model = createValidityModel();
  const modes = { airdata: 'nominal', inertial: 'nominal', gnss: 'nominal' };
  const subscribers = new Set();
  let declutter = 3;
  for (const id of Object.keys(modes)) model.sample(id, sampleFor(id, flightState(0)));
  function get() {
    const state = model.snapshot();
    const displayState = Object.assign({}, ...Object.values(state.sources).map(s => s.value || s.lastGood || {}));
    return { ...state, declutter, displayState };
  }
  const emit = () => { for (const fn of subscribers) fn(get()); };
  return {
    get,
    subscribe(fn) { subscribers.add(fn); return () => subscribers.delete(fn); },
    setSource(id, state) {
      if (!Object.hasOwn(modes, id)) throw new RangeError('Unknown source');
      const now = model.snapshot().time;
      model.setSource(id, state, state === 'nominal' ? sampleFor(id, flightState(motion ? now : 0)) : undefined);
      modes[id] = state;
      emit();
    },
    setDeclutter(level) {
      if (!Number.isInteger(level) || level < 1 || level > 5) throw new RangeError('Declutter must be 1 to 5');
      declutter = level; emit();
    },
    tick(dt) {
      model.tick(dt);
      const now = model.snapshot().time;
      for (const [id, mode] of Object.entries(modes)) {
        if (mode === 'nominal') model.sample(id, sampleFor(id, flightState(motion ? now : 0)));
      }
      emit();
    },
    emit,
  };
}
