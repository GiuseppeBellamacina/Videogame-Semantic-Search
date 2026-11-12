// Single source of truth for entity colours, sizes and labels (canvas + components).
export const NODE_COLORS: Record<string, string> = {
  VideoGame: "#d4573b",
  Developer: "#d9a441",
  Publisher: "#7fae7a",
  Genre: "#c98f7a",
  Platform: "#5aa0a6",
  Character: "#c27ba0",
  Franchise: "#a89a6b",
  Award: "#e0b04c",
  GameEngine: "#6f8fb5",
  GameMode: "#8fb8a8",
  Unknown: "#6b675e",
};

export const NODE_SIZES: Record<string, number> = {
  VideoGame: 9,
  Developer: 8,
  Publisher: 8,
  Genre: 6,
  Platform: 7,
  Character: 5,
  Franchise: 9,
  Award: 6,
  GameEngine: 7,
  GameMode: 6,
  Unknown: 5,
};

export const TYPE_LABELS: Record<string, string> = {
  VideoGame: "Videogioco",
  Developer: "Sviluppatore",
  Publisher: "Publisher",
  Genre: "Genere",
  Platform: "Piattaforma",
  Character: "Personaggio",
  Franchise: "Serie",
  Award: "Premio",
  GameEngine: "Motore",
  GameMode: "Modalità",
  Unknown: "Altro",
};

/** Defined game classes are shown as plain video games. */
export const GAME_TYPES = new Set([
  "VideoGame",
  "AwardWinningGame",
  "FranchiseGame",
]);

/** Entity types for which a picture is worth fetching. */
export const IMAGE_TYPES = new Set([
  "VideoGame",
  "AwardWinningGame",
  "FranchiseGame",
  "Developer",
  "Publisher",
  "Platform",
  "Franchise",
  "GameEngine",
  "Character",
]);

export const typeColor = (t: string) => NODE_COLORS[t] ?? NODE_COLORS.Unknown;
export const typeSize = (t: string) => NODE_SIZES[t] ?? NODE_SIZES.Unknown;
export const typeLabel = (t: string) => TYPE_LABELS[t] ?? t;
