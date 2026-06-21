export type ISODateTime = string;

export type HealthResponse = {
  database: string;
  detail?: string;
  status: "healthy" | "unhealthy" | string;
};

export type RepositoryCreate = {
  branch?: string | null;
  clone_url?: string | null;
  index_now?: boolean;
  local_path?: string | null;
  name: string;
};

export type Repository = {
  clone_url: string | null;
  created_at: ISODateTime;
  current_ref: string | null;
  default_branch: string | null;
  id: number;
  indexed_at: ISODateTime | null;
  last_indexed_commit: string | null;
  local_path: string | null;
  name: string;
  repo_metadata: Record<string, unknown> | null;
  status: string;
  updated_at: ISODateTime;
};

export type RepositoryList = {
  items: Repository[];
  limit: number;
  skip: number;
  total: number;
};

export type IndexRepositoryRequest = {
  max_commits?: number | null;
  ref?: string | null;
};

export type IndexRepositoryResponse = {
  chunks_indexed: number;
  commits_indexed: number;
  current_ref: string | null;
  dependency_edges_indexed: number;
  embeddings_indexed: number;
  files_indexed: number;
  files_skipped: number;
  indexed_at: ISODateTime | null;
  parser_errors: Record<string, unknown>[];
  repository_id: number;
  status: string;
  symbols_indexed: number;
  warnings: string[];
};

export type IndexStatusResponse = {
  chunk_count: number;
  commit_count: number;
  current_ref: string | null;
  dependency_edge_count: number;
  file_count: number;
  indexed_at: ISODateTime | null;
  last_indexed_commit: string | null;
  repository_id: number;
  status: string;
  symbol_count: number;
};
