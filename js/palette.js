// Shared constants: world scale, the colour palette, and animation timings.

export const TILE = 1.0;

// heading int -> rotation about Y so the character (built facing -Z) points the
// right way. Matches world.py: 0=N(-Z) 1=E(+X) 2=S(+Z) 3=W(-X).
export const headingAngle = (h) => (-h * Math.PI) / 2;

// Warm, low-poly palettes. Light is the original look; dark shifts the world
// toward a night-island feel inspired by Swift Playgrounds.
export const PALETTES = {
  light: {
    sky: 0xbfe6ff,
    fog: 0xbfe6ff,
    grass: 0x8ac765,
    grassDark: 0x6fae49,
    dirt: 0xb98a55,
    water: 0x57b8e0,
    waterOpacity: 0.92,
    lava: 0xe7430f,
    lavaEmissive: 0xd02400,
    stone: 0x8b94a0,
    stoneLight: 0xa9b2bd,
    doorFrame: 0x6b7480,
    hemiSky: 0xbfe6ff,
    hemiGround: 0x6fae49,
    sun: 0xfff1d6,
    sunIntensity: 1.5,
    ambient: 0xffffff,
    ambientIntensity: 0.25,
    exposure: 1.05,
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
  },
  dark: {
    sky: 0x0b1645,
    fog: 0x0b1645,
    grass: 0x4f9b4d,
    grassDark: 0x326a34,
    dirt: 0x98663e,
    water: 0x168ce8,
    waterOpacity: 0.88,
    lava: 0xff5a1f,
    lavaEmissive: 0xff2b00,
    stone: 0x55606d,
    stoneLight: 0x74808e,
    doorFrame: 0x404a58,
    hemiSky: 0x7da4ff,
    hemiGround: 0x264c2b,
    sun: 0xd7e5ff,
    sunIntensity: 1.05,
    ambient: 0xb7c8ff,
    ambientIntensity: 0.58,
    exposure: 1.1,
    // Characters keep their identity but read a bit richer under night lighting.
    moss: 0x84b84d,
    mossDark: 0x527f34,
    stem: 0x5d9341,
    bud: 0xbde37f,
    leaf: 0x95cf56,
    eyeDark: 0x1d1721,
    // collectibles
    gem: 0xff426d,
    gemEmissive: 0xff1f55,
    goal: 0xffe067,
  },
};

export const normalizeTheme = (theme) => (theme === "dark" ? "dark" : "light");
export const colorsForTheme = (theme) => PALETTES[normalizeTheme(theme)];
export const COLORS = PALETTES.light;

// Base animation durations (ms), divided by the speed multiplier.
export const DUR = { move: 520, turn: 380, collect: 560, blocked: 560 };
