import type { QueryResponse } from "@/types";

// Module-level cache: persists for the entire browser session
const cache = new Map<string, QueryResponse>();

export function getCached(question: string): QueryResponse | undefined {
  return cache.get(question.trim().toLowerCase());
}

export function setCached(question: string, response: QueryResponse): void {
  cache.set(question.trim().toLowerCase(), response);
}

export function hasCached(question: string): boolean {
  return cache.has(question.trim().toLowerCase());
}

// Suggestions that get pre-fetched in the background on app load
export const SUGGESTIONS = [
  "Quali giochi ha sviluppato FromSoftware?",
  "Top 10 giochi con il punteggio Metacritic più alto",
  "Giochi RPG usciti nel 2023",
  "Giochi della serie Zelda",
  "Quali giochi sono disponibili su PlayStation 5?",
  "Giochi sviluppati da Nintendo dopo il 2020",
];
