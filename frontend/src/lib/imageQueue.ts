import { assetUrl, fetchImages } from "@/lib/api";
import { IMAGE_TYPES } from "@/lib/theme";

/**
 * Client side of the image store: one lookup per (type, name) for the whole session,
 * grouped into batched requests with a small concurrency limit. Urgent items (hover,
 * selection) jump the queue.
 */
const BATCH = 12;
const MAX_PARALLEL = 3;

type Job = {
  key: string;
  name: string;
  type: string;
  resolve: (url: string | null) => void;
};

const done = new Map<string, string | null>();
const pending = new Map<string, Promise<string | null>>();
const queue: Job[] = [];
let running = 0;

const norm = (t: string) =>
  t === "AwardWinningGame" || t === "FranchiseGame" ? "VideoGame" : t;

export const imageKey = (type: string, name: string) => `${norm(type)}|${name}`;

/** Cached result if known: string = found, null = no image, undefined = not asked yet. */
export const peekImage = (type: string, name: string) =>
  done.get(imageKey(type, name));

export function requestImage(
  type: string,
  name: string,
  urgent = false,
): Promise<string | null> {
  if (!IMAGE_TYPES.has(type) || !name) return Promise.resolve(null);
  const key = imageKey(type, name);
  if (done.has(key)) return Promise.resolve(done.get(key)!);
  const existing = pending.get(key);
  if (existing) {
    if (urgent) bump(key);
    return existing;
  }
  const p = new Promise<string | null>((resolve) => {
    const job: Job = { key, name, type: norm(type), resolve };
    if (urgent) queue.unshift(job);
    else queue.push(job);
  });
  pending.set(key, p);
  void pump();
  return p;
}

function bump(key: string) {
  const i = queue.findIndex((j) => j.key === key);
  if (i > 0) queue.unshift(queue.splice(i, 1)[0]);
}

function pump() {
  while (running < MAX_PARALLEL && queue.length) {
    const jobs = queue.splice(0, BATCH);
    running++;
    fetchImages(jobs.map((j) => ({ name: j.name, type: j.type })))
      .then((found) => {
        for (const j of jobs) {
          const url = assetUrl(found[`${j.type}|${j.name}`] ?? null);
          done.set(j.key, url);
          pending.delete(j.key);
          j.resolve(url);
        }
      })
      .catch(() => {
        // network trouble: leave the keys unknown so a later request retries
        for (const j of jobs) {
          pending.delete(j.key);
          j.resolve(null);
        }
      })
      .finally(() => {
        running--;
        pump();
      });
  }
}
