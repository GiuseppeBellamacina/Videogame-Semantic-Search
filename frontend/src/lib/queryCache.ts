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

// Example questions: each one is a preset in backend/presets.json, answered without the LLM
export const SUGGESTIONS = [
  "Quali giochi ha sviluppato FromSoftware?",
  "Top 10 giochi con il punteggio Metacritic più alto",
  "Quali giochi hanno vinto il Game of the Year?",
  "Quali giochi sono disponibili su PlayStation 5?",
  "Giochi della serie Zelda",
  "Giochi RPG usciti nel 2023",
  "Giochi sviluppati da Nintendo dopo il 2020",
  "Giochi pubblicati da Rockstar Games",
  "Giochi della serie Horizon",
  "Giochi cooperativi con il punteggio più alto",
  "Su quali piattaforme è disponibile Elden Ring?",
  "Mostra le relazioni dei giochi di FromSoftware",
];
