// Character registry. Map a name (the widget's `character` trait) to a class,
// and instantiate it. To add a character: implement the Character contract (see
// character.js) and register it here.

import { Character } from "./character.js";
import { MossballCharacter } from "./mossball.js";
import { RoverCharacter } from "./rover.js";

const REGISTRY = {
  mo: MossballCharacter,
  rover: RoverCharacter,
};

export const DEFAULT_CHARACTER = "mo";

export function characterNames() {
  return Object.keys(REGISTRY);
}

export function createCharacter(name) {
  const Cls = REGISTRY[name] || REGISTRY[DEFAULT_CHARACTER];
  return new Cls();
}

export { Character };
