// Shared constants: world scale, the colour palette, and animation timings.

export const TILE = 1.0;

// heading int -> rotation about Y so the character (built facing -Z) points the
// right way. Matches world.py: 0=N(-Z) 1=E(+X) 2=S(+Z) 3=W(-X).
export const headingAngle = (h) => (-h * Math.PI) / 2;

// Warm, low-poly palette.
export const COLORS = {
  sky: 0xbfe6ff,
  grass: 0x8ac765,
  grassDark: 0x6fae49,
  dirt: 0xb98a55,
  water: 0x57b8e0,
  // Mo the Mossball
  moss: 0x8fbf52,
  mossDark: 0x6f9c3b,
  stem: 0x6fa244,
  bud: 0xc6e38d,
  leaf: 0xa6d566,
  eyeDark: 0x3a2f3a,
  // collectibles
  gem: 0x37d0ff,
  gemEmissive: 0x1fa9d6,
  goal: 0xffd34d,
};

// Base animation durations (ms), divided by the speed multiplier.
export const DUR = { move: 520, turn: 380, collect: 560, blocked: 560 };
