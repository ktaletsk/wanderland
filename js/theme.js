import { normalizeTheme } from "./palette.js";

const THEME_KEYS = ["theme", "_theme", "color_scheme", "colorScheme"];
const DARK_RE = /(^|[-_\s])(dark|night|black)([-_\s]|$)/i;
const LIGHT_RE = /(^|[-_\s])(light|day|white)([-_\s]|$)/i;

function modelTheme(model) {
  if (!model || typeof model.get !== "function") return null;
  for (const key of THEME_KEYS) {
    const value = model.get(key);
    const theme = parseTheme(value);
    if (theme) return theme;
  }
  return null;
}

function parseTheme(value) {
  if (value == null) return null;
  const text = String(value);
  if (DARK_RE.test(text)) return "dark";
  if (LIGHT_RE.test(text)) return "light";
  return null;
}

function nodeTheme(node) {
  if (!node) return null;
  const attrs = ["data-theme", "data-bs-theme", "data-color-mode", "data-jp-theme-light", "theme"];
  for (const attr of attrs) {
    if (node.hasAttribute && node.hasAttribute(attr)) {
      const theme = parseTheme(node.getAttribute(attr));
      if (theme) return theme;
    }
  }
  const cls = node.className && typeof node.className === "string" ? node.className : "";
  return parseTheme(cls);
}

function hostTheme(el) {
  for (let node = el; node; node = node.parentElement) {
    const theme = nodeTheme(node);
    if (theme) return theme;
  }
  for (const node of [document.documentElement, document.body]) {
    const theme = nodeTheme(node);
    if (theme) return theme;
  }
  return null;
}

function cssTheme() {
  const style = window.getComputedStyle(document.documentElement);
  const scheme = style.colorScheme || style.getPropertyValue("color-scheme");
  const theme = parseTheme(scheme);
  if (theme) return theme;
  return null;
}

export function detectTheme(el, model) {
  return normalizeTheme(
    modelTheme(model) ||
      hostTheme(el) ||
      cssTheme() ||
      (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );
}

export function watchTheme(el, model, onChange) {
  let current = detectTheme(el, model);
  const apply = () => {
    const next = detectTheme(el, model);
    if (next === current) return;
    current = next;
    onChange(next);
  };

  const observer = new MutationObserver(apply);
  for (const node of [document.documentElement, document.body, el]) {
    if (node) {
      observer.observe(node, {
        attributes: true,
        attributeFilter: ["class", "style", "data-theme", "data-bs-theme", "data-color-mode", "data-jp-theme-light", "theme"],
      });
    }
  }

  const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  if (media) {
    if (media.addEventListener) media.addEventListener("change", apply);
    else media.addListener(apply);
  }

  const modelHandlers = [];
  if (model && typeof model.on === "function") {
    for (const key of THEME_KEYS) {
      const event = `change:${key}`;
      model.on(event, apply);
      modelHandlers.push(event);
    }
  }

  return () => {
    observer.disconnect();
    if (media) {
      if (media.removeEventListener) media.removeEventListener("change", apply);
      else media.removeListener(apply);
    }
    if (model && typeof model.off === "function") {
      for (const event of modelHandlers) model.off(event, apply);
    }
  };
}
