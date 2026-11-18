export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  size: number;
  imageUrl?: string;
  autoFetchImage?: boolean;
  x?: number;
  y?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface QueryResult {
  [key: string]: string | null;
}

export interface QueryResponse {
  results: QueryResult[];
  graph: GraphData;
  sparql: string;
  total_rows: number;
  success: boolean;
  truncated?: boolean;
}

export interface NodeDetails {
  uri: string;
  label: string;
  type: string;
  classes?: string[];
  properties: Record<string, string>;
  outgoing_relations: {
    predicate: string;
    target_uri: string;
    target_label: string;
    target_type: string;
  }[];
  incoming_relations: {
    predicate: string;
    source_uri: string;
    source_label: string;
    source_type: string;
  }[];
  total_incoming?: number;
  truncated?: boolean;
}

export interface NodeDetailResponse {
  details: NodeDetails;
  graph: GraphData;
}

export interface OntologyStats {
  total_triples: number;
  games: number;
  developers: number;
  publishers: number;
  genres: number;
  platforms: number;
  characters: number;
  franchises: number;
  awards: number;
}

export interface Suggestion {
  label: string;
  uri: string;
  type: string;
}

export interface BuilderField {
  field: string;
  label: string;
  kind: "entity" | "number" | "year" | "month" | "text" | "class";
  target?: string;
  options?: string[];
  ops: string[];
}

export interface BuilderSchema {
  fields: BuilderField[];
  orders: string[];
}

export interface BuilderFilterInput {
  field: string;
  op: string;
  value: string | number;
}

export interface BuilderRequest {
  filters: BuilderFilterInput[];
  order_by: string;
  limit: number;
  output: "table" | "graph";
}

export type SearchPhase =
  | "generating"
  | "validating"
  | "executing"
  | "building_graph";

export type SearchEvent =
  | { type: "phase"; phase: SearchPhase; attempt?: number }
  | { type: "query"; sparql: string }
  | { type: "retry"; reason: "syntax" | "error" | "empty" }
  | { type: "done"; cached: boolean; result: QueryResponse }
  | { type: "error"; detail: string };

export interface SearchProgress {
  phase: SearchPhase;
  attempt: number;
  retry?: "syntax" | "error" | "empty";
  sparql?: string;
}
