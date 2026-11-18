// Self-check of relations.ts: `bun run src/lib/relations.check.ts` (throws on the first failure).
import { controlPoint, curvatures, dedupeLinks, orient } from "./relations";

const eq = (a: unknown, b: unknown, what: string) => {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${what}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
};

const L = (source: string, target: string, label: string) => ({ source, target, label });
// a game and a company that both develops and publishes it, each fact in both directions
const links = [
  L("g", "c", "developedBy"),
  L("c", "g", "developerOf"),
  L("g", "c", "publishedBy"),
  L("c", "g", "publisherOf"),
  L("g", "h", "sharesDeveloperWith"),
  L("h", "g", "sharesDeveloperWith"),
];
const d = dedupeLinks(links);
eq(d.map((l) => l.label), ["developedBy", "publishedBy", "sharesDeveloperWith"], "one link per fact, forward kept");

// only the inverse is there: it is kept
eq(dedupeLinks([L("c", "g", "developerOf")]).length, 1, "lone inverse kept");

const dev = d[0];
eq(orient(dev, "g", false), { flip: false, label: "developedBy" }, "game selected: developedBy, game -> company");
eq(orient(dev, "c", false), { flip: true, label: "developerOf" }, "company selected: developerOf, company -> game");
eq(orient(dev, null, false), { flip: false, label: "developedBy" }, "nothing selected: forward");
eq(orient(dev, "x", false), { flip: false, label: "developedBy" }, "another node selected: forward");
eq(orient(dev, "g", true), { flip: true, label: "developerOf" }, "invert: game selected reads developerOf");
eq(orient(dev, "c", true), { flip: false, label: "developedBy" }, "invert: company selected reads developedBy");
// the stored link is the inverse one: the reading must be the same
const inv = L("c", "g", "developerOf");
eq(orient(inv, "g", false), { flip: true, label: "developedBy" }, "stored inverse, game selected");
eq(orient(inv, "c", false), { flip: false, label: "developerOf" }, "stored inverse, company selected");
eq(orient(d[2], "g", true), { flip: false, label: "sharesDeveloperWith" }, "symmetric relations never change");

// the two relations between g and c are spread to opposite sides, whatever the reading
const cv = curvatures(d.slice(0, 2));
eq([...cv.values()].map((x) => Math.sign(x)), [-1, 1], "parallel arcs on opposite sides");
eq(curvatures([dev]).get(dev), 0, "a single arc is straight");
const a = { id: "g", x: 0, y: 0 };
const c = { id: "c", x: 100, y: 0 };
eq(controlPoint(a, c, 0.3), controlPoint(c, a, 0.3), "same side from either end");
console.log("relations.ts: ok");
