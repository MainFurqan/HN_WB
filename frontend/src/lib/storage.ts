// Tiny localStorage wrapper used to persist demo state across country swaps.
// Keys are namespaced under "unmapped:" so they don't collide.

export const KEY = {
  description: "unmapped:description",
  name: "unmapped:name",
  lang: "unmapped:lang",
  profile: "unmapped:profile",
};

export function load(key: string, fallback = ""): string {
  if (typeof window === "undefined") return fallback;
  try {
    return window.localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* quota or denied */
  }
}
