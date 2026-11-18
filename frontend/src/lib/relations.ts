// Relations between the same two nodes: one arc per relation (not one per direction), the verb read
// from the selected node, parallel arcs spread apart. Pure functions, no React: see relations.check.ts.

/** [forward, inverse]: the forward one has the game (or the "main" entity) as subject. */
export const INVERSE_PAIRS: [string, string][] = [
  ["developedBy", "developerOf"],
  ["publishedBy", "publisherOf"],
  ["hasGenre", "genreOf"],
  ["availableOn", "platformFor"],
  ["hasCharacter", "appearsIn"],
  ["belongsTo", "includes"],
  ["wonAward", "awardWonBy"],
  ["madeWith", "engineUsedIn"],
  ["hasGameMode", "modeInGame"],
  ["sequelOf", "hasSequel"],
  ["hasReview", "reviewedGame"],
  ["hasEvent", "eventFor"],
];

const FORWARD_OF = new Map<string, string>();
const INVERSE_OF = new Map<string, string>();
for (const [f, r] of INVERSE_PAIRS) {
  FORWARD_OF.set(f, f).set(r, f);
  INVERSE_OF.set(f, r).set(r, f);
}

type End = string | { id: string };
type Rel = { source: End; target: End; label: string };
const idOf = (e: End) => (typeof e === "string" ? e : e.id);

/** The forward name of a relation (itself if it has no inverse). */
export const canonical = (label: string) => FORWARD_OF.get(label) ?? label;
export const isInvertible = (label: string) => INVERSE_OF.has(label);

const pairKey = (a: string, b: string) => (a < b ? `${a}\u0001${b}` : `${b}\u0001${a}`);

/**
 * One link per (two nodes, relation): `developedBy` and `developerOf` between the same two nodes are the
 * same fact, and so are the two directions of a symmetric one (sharesDeveloperWith). The link kept is the
 * forward one when present. The kept objects are the originals (the force graph mutates them).
 */
export function dedupeLinks<T extends Rel>(links: T[]): T[] {
  const kept = new Map<string, T>();
  for (const l of links) {
    const key = `${pairKey(idOf(l.source), idOf(l.target))}\u0002${canonical(l.label)}`;
    const cur = kept.get(key);
    if (!cur || (isInvertible(l.label) && FORWARD_OF.get(l.label) === l.label && cur.label !== l.label)) {
      kept.set(key, l);
    }
  }
  return links.filter((l) => kept.get(`${pairKey(idOf(l.source), idOf(l.target))}\u0002${canonical(l.label)}`) === l);
}

/**
 * How to draw a link: the subject is the selected node when it is one of the two, otherwise the
 * forward subject (the game); `invert` flips every invertible relation. `flip` = draw target -> source.
 */
export function orient(link: Rel, selected: string | null | undefined, invert: boolean): { flip: boolean; label: string } {
  const s = idOf(link.source);
  const t = idOf(link.target);
  const f = FORWARD_OF.get(link.label);
  if (!f || s === t) return { flip: false, label: link.label };
  const forwardSubject = link.label === f ? s : t;
  let subject = selected === s || selected === t ? (selected as string) : forwardSubject;
  if (invert) subject = subject === s ? t : s;
  return {
    flip: subject !== s,
    label: subject === forwardSubject ? f : INVERSE_OF.get(f)!,
  };
}

/** Curvature of each link: 0 when alone between its two nodes, spread symmetrically otherwise. */
export function curvatures<T extends Rel>(links: T[], step = 0.32): Map<T, number> {
  const groups = new Map<string, T[]>();
  for (const l of links) {
    const k = pairKey(idOf(l.source), idOf(l.target));
    (groups.get(k) ?? groups.set(k, []).get(k)!).push(l);
  }
  const out = new Map<T, number>();
  for (const g of groups.values()) g.forEach((l, i) => out.set(l, g.length === 1 ? 0 : (i - (g.length - 1) / 2) * step));
  return out;
}

/** Control point of the quadratic curve of a link. The side is fixed by the ids (not by the drawing
 *  direction), so it does not move when a relation is read the other way. */
export function controlPoint(
  a: { id: string; x: number; y: number },
  b: { id: string; x: number; y: number },
  curvature: number,
): { x: number; y: number } {
  const [p, q] = a.id < b.id ? [a, b] : [b, a];
  const dx = q.x - p.x;
  const dy = q.y - p.y;
  const len = Math.hypot(dx, dy) || 1;
  return { x: (a.x + b.x) / 2 - (dy / len) * len * curvature, y: (a.y + b.y) / 2 + (dx / len) * len * curvature };
}
