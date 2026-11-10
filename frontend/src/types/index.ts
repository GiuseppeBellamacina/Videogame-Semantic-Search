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
}

export interface NodeDetails {
  uri: string;
  label: string;
  type: string;
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
  kind: "entity" | "number" | "year" | "text" | "class";
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
}
