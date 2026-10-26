// Shared helpers for the site's pages. Plain ES modules, no libraries.
// Text from data files is always inserted with textContent, never as HTML.

export const SOURCES = {
  camera: { label: "Camera", color: "var(--s-camera)" },
  phone_gnss: { label: "Phone GNSS", color: "var(--s-phone)" },
  tag_gnss: { label: "Tag GNSS", color: "var(--s-tag)" },
};

export function sourceInfo(name) {
  return SOURCES[name] || { label: name.replace(/_/g, " "), color: "var(--s-other)", other: true };
}

// The fallback ladder, in order. Status colours carry severity, and every use
// pairs the colour with the icon and the label.
export const MODES = {
  tracking: { label: "Tracking", icon: "●", color: "var(--good)" },
  degraded: { label: "Degraded", icon: "◐", color: "var(--warning)" },
  dead_reckoning: { label: "Dead reckoning", icon: "○", color: "var(--serious)" },
  hold: { label: "Hold", icon: "‖", color: "var(--serious)" },
  return_home_requested: { label: "Return home requested", icon: "⌂", color: "var(--critical)" },
};

export function modeInfo(mode) {
  return MODES[mode] || { label: String(mode), icon: "?", color: "var(--muted)" };
}

const SVG_NS = "http://www.w3.org/2000/svg";

export function svg(tag, attrs = {}, parent) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value !== undefined && value !== null) node.setAttribute(key, value);
  }
  if (parent) parent.appendChild(node);
  return node;
}

export function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "style" && typeof value === "object") Object.assign(node.style, value);
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(typeof child === "string" || typeof child === "number" ? document.createTextNode(String(child)) : child);
  }
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const money0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function usd(value, whole = false) {
  return (whole ? money0 : money).format(value);
}

export function usdRange([low, high], whole = false) {
  return low === high ? usd(low, whole) : `${usd(low, whole)} to ${usd(high, whole)}`;
}

export function fixed(value, digits = 2) {
  return Number(value).toFixed(digits);
}

export function signed(value, digits = 2) {
  const text = Math.abs(value).toFixed(digits);
  return (value < 0 ? "−" : "+") + text;
}

export function percent(share) {
  return `${Math.round(share * 100)}%`;
}

// The smallest round number at or above value, for an axis maximum or a step.
export function niceMax(value) {
  const steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
  const power = 10 ** Math.floor(Math.log10(value));
  for (const s of steps) if (s * power >= value) return s * power;
  return 10 * power;
}

export async function fetchJSON(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.json();
}

// One floating tooltip per page. Rows are {value, label, color}; the value leads.
export function makeTooltip() {
  const tip = h("div", { class: "tooltip", role: "status", hidden: true });
  document.body.appendChild(tip);
  return {
    show(title, rows, x, y) {
      clear(tip);
      if (title) tip.appendChild(h("div", { class: "title" }, title));
      for (const row of rows) {
        tip.appendChild(
          h("div", { class: "row" },
            row.color ? h("span", { class: "key-line", style: { color: row.color } }) : null,
            h("strong", {}, row.value),
            row.label ? h("span", {}, row.label) : null,
          ),
        );
      }
      tip.hidden = false;
      const pad = 14;
      const box = tip.getBoundingClientRect();
      let left = x + pad;
      let top = y + pad;
      if (left + box.width > window.innerWidth - 8) left = x - box.width - pad;
      if (top + box.height > window.innerHeight - 8) top = y - box.height - pad;
      tip.style.left = `${Math.max(8, left)}px`;
      tip.style.top = `${Math.max(8, top)}px`;
    },
    hide() {
      tip.hidden = true;
    },
  };
}

const THEMES = ["auto", "light", "dark"];
const THEME_LABELS = { auto: "◐ Auto", light: "☀ Light", dark: "☾ Dark" };

function readTheme() {
  try {
    const saved = localStorage.getItem("theme");
    return THEMES.includes(saved) ? saved : "auto";
  } catch {
    return "auto";
  }
}

function applyTheme(theme, button) {
  if (theme === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
  if (button) {
    button.textContent = THEME_LABELS[theme];
    button.setAttribute("aria-label", `Theme: ${theme}. Change theme`);
  }
}

// Theme toggle and the build line in the footer, shared by every page.
export function initPage() {
  const button = document.querySelector("[data-theme-toggle]");
  let theme = readTheme();
  applyTheme(theme, button);
  button?.addEventListener("click", () => {
    theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    applyTheme(theme, button);
    try {
      localStorage.setItem("theme", theme);
    } catch {
      // Storage can be blocked; the toggle still works for this visit.
    }
  });
  const line = document.querySelector("[data-build]");
  if (line) {
    fetchJSON("data/build.json")
      .then((info) => {
        const parts = [];
        if (info.commit) parts.push(`commit ${info.commit}`);
        if (info.built) parts.push(info.built);
        line.textContent = parts.length ? `Built from ${parts.join(", ")}.` : "";
      })
      .catch(() => {
        line.textContent = "";
      });
  }
}
