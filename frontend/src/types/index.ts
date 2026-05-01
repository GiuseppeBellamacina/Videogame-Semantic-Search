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
