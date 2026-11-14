import { assetUrl, fetchImages, retryImageApi } from "@/lib/api";
import { IMAGE_TYPES } from "@/lib/theme";

/**
 * Client side of the image store: one lookup per (type, name) for the whole session,
 * grouped into batched requests with a small concurrency limit. Urgent items (hover,
 * selection) jump the queue.
 */
const BATCH = 10;
const MAX_PARALLEL = 3;
const MAX_TRIES = 6;

type Job = {
  key: string;
  name: string;
  type: string;
  resolve: (url: string | null) => void;
  tries?: number;
};

const done = new Map<string, string | null>();
const pending = new Map<string, Promise<string | null>>();
const queue: Job[] = [];
let running = 0;

const norm = (t: string) =>
  t === "AwardWinningGame" || t === "FranchiseGame" ? "VideoGame" : t;

const listeners = new Set<() => void>();
/** Called when a picture is replaced (retry): hooks and the canvas repaint. */
export const onImagesChanged = (cb: () => void) => {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
};

/** Another picture for this entity; null when Wikipedia has no other candidate. */
export async function retryImage(type: string, name: string): Promise<string | null> {
  const url = assetUrl(await retryImageApi(name, norm(type)));
  if (url) {
    done.set(imageKey(type, name), url);
    listeners.forEach((cb) => cb());
  }
  return url;
}

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

/** The server could not tell (Wikimedia rate limit, network): not "no image". Try again later,
 *  a few times; after that leave the key unknown so a later request asks anew. */
function later(job: Job, seconds: number) {
  job.tries = (job.tries ?? 0) + 1;
  if (job.tries >= MAX_TRIES) {
    pending.delete(job.key);
    job.resolve(null);
    return;
  }
  setTimeout(() => {
    queue.push(job);
    void pump();
  }, Math.min(Math.max(seconds, 3), 120) * 1000);
}

function pump() {
  while (running < MAX_PARALLEL && queue.length) {
    const jobs = queue.splice(0, BATCH);
    running++;
    fetchImages(jobs.map((j) => ({ name: j.name, type: j.type })))
      .then(({ images, retry }) => {
        for (const j of jobs) {
          const k = `${j.type}|${j.name}`;
          if (k in retry || !(k in images)) {
            later(j, retry[k] ?? 15);
            continue;
          }
          const url = assetUrl(images[k] ?? null);
          done.set(j.key, url);
          pending.delete(j.key);
          j.resolve(url);
        }
      })
      .catch(() => {
        for (const j of jobs) later(j, 10);
      })
      .finally(() => {
        running--;
        pump();
      });
  }
}
