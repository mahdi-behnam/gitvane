export type ISODateTime = string;

export type HealthResponse = {
  database: string;
  detail?: string;
  status: "healthy" | "unhealthy" | string;
};

export type RepositoryCreate = {
  branch?: string | null;
  clone_url: string;
  index_now?: boolean;
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

export type ChangedFileInput = {
  change_type?: string;
  changed_lines?: [number, number][];
  old_path?: string | null;
  path: string;
};

export type SemanticSearchRequest = {
  query: string;
  repository_id: number;
  top_k?: number;
};

export type SemanticSearchResult = {
  end_line: number;
  path: string;
  score: number;
  snippet: string;
  start_line: number;
  symbol: string | null;
};

export type SemanticSearchResponse = {
  results: SemanticSearchResult[];
};

export type ChangedSymbol = {
  end_line: number;
  path: string;
  qualified_name: string;
  start_line: number;
  symbol_type: string;
};

export type ImpactReason = {
  confidence: number;
  evidence: Record<string, unknown>;
  message: string;
  type: string;
};

export type TestRecommendation = {
  linked_files: string[];
  path: string;
  reason: string | null;
  score: number;
};

export type ImpactedFile = {
  component_scores: Record<string, number>;
  path: string;
  rank: number;
  reasons: ImpactReason[];
  recommended_tests: TestRecommendation[];
  score: number;
};

export type ImpactAnalyzeRequest = {
  base_ref?: string | null;
  changed_files?: ChangedFileInput[] | null;
  head_ref?: string | null;
  include_changed_files_in_predictions?: boolean;
  include_explanation?: boolean;
  max_dependency_depth?: number;
  raw_diff?: string | null;
  repository_id: number;
  top_k?: number;
};

export type ImpactAnalyzeResponse = {
  analysis_run_id: number;
  base_ref: string | null;
  changed_files: ChangedFileInput[];
  changed_symbols: ChangedSymbol[];
  head_ref: string | null;
  impacted_files: ImpactedFile[];
  llm_explanation: string | null;
  recommended_tests: TestRecommendation[];
  repository_id: number;
  risk_summary: {
    highest_risk_files: Record<string, unknown>[];
  };
};

export type ImpactRunResponse = {
  analysis_run_id: number;
  changed_files: Record<string, unknown>[];
  changed_symbols: Record<string, unknown>[];
  input_mode: "git_diff" | "raw_diff" | "changed_files";
  predictions: ImpactedFile[];
  repository_id: number;
  status: string;
};

export type TestRecommendationRequest = {
  changed_files: ChangedFileInput[];
  impacted_files?: string[];
  repository_id: number;
  top_k?: number;
};

export type TestRecommendationResponse = {
  changed_files: ChangedFileInput[];
  recommended_tests: TestRecommendation[];
  repository_id: number;
};

export type RepositoryRiskArgs = {
  include_tests?: boolean;
  language?: string | null;
  repositoryId: number;
  top_k?: number;
};

export type RiskFile = {
  components: Record<string, number>;
  path: string;
  reasons: string[];
  risk_score: number;
};

export type RepositoryRiskResponse = {
  files: RiskFile[];
  metadata: Record<string, unknown>;
  repository_id: number;
};

export type EvaluationMethod =
  | "dependency_only"
  | "semantic_only"
  | "cochange_only"
  | "hybrid";

export type EvaluationRunRequest = {
  commit_limit?: number;
  k_values?: number[];
  methods?: EvaluationMethod[];
  name?: string;
  repository_id: number;
};

export type EvaluationRunResponse = {
  evaluation_run_id: number;
  status: string;
  summary: Record<string, unknown>;
};

export type EvaluationStatusResponse = {
  commit_limit: number;
  error_message: string | null;
  evaluation_run_id: number;
  methods: string[];
  name: string;
  repository_id: number;
  status: string;
  summary: Record<string, unknown>;
};

export type EvaluationReportResponse = {
  evaluation_run_id: number;
  markdown: string;
};

export type GraphNode = {
  id: number;
  is_generated: boolean;
  is_test: boolean;
  language: string;
  loc: number;
  path: string;
};

export type GraphEdge = {
  confidence: number;
  edge_type: string;
  evidence: Record<string, unknown>;
  id: number;
  source_file_id: number;
  source_path: string;
  target_file_id: number;
  target_path: string;
};

export type GraphResponse = {
  edges: GraphEdge[];
  nodes: GraphNode[];
  repository_id: number;
};

export type UserCreate = {
  email: string;
  password: string;
  full_name: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
};

export type UserResponse = {
  id: number;
  email: string;
  full_name: string;
};

