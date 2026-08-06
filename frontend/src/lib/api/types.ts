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
  pat?: string | null;
};

export type Repository = {
  clone_url: string | null;
  created_at: ISODateTime;
  current_ref: string | null;
  default_branch: string | null;
  id: string;
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
  repository_id: string;
  status: string;
  symbols_indexed: number;
  warnings: string[];
};

export type IndexingProgressEvent = {
  chunks_processed: number;
  chunks_total: number;
  error: string | null;
  estimated_seconds_remaining: number | null;
  files_processed: number;
  files_total: number;
  phase: string;
  phase_name: string;
  progress_percentage: number;
  repository_id: string;
  status: string;
};

export type IndexStatusResponse = {
  chunk_count: number;
  commit_count: number;
  current_ref: string | null;
  dependency_edge_count: number;
  file_count: number;
  indexed_at: ISODateTime | null;
  last_indexed_commit: string | null;
  progress?: IndexingProgressEvent | null;
  repository_id: string;
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
  repository_id: string;
  top_k?: number;
};

export type SemanticSearchResult = {
  end_line: number;
  language?: string | null;
  path: string;
  score: number;
  signature?: string | null;
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
  repository_id: string;
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
  repository_id: string;
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
  repository_id: string;
  status: string;
};

export type TestRecommendationRequest = {
  changed_files: ChangedFileInput[];
  impacted_files?: string[];
  repository_id: string;
  top_k?: number;
};

export type TestRecommendationResponse = {
  changed_files: ChangedFileInput[];
  recommended_tests: TestRecommendation[];
  repository_id: string;
};

export type RepositoryRiskArgs = {
  include_tests?: boolean;
  language?: string | null;
  path_search?: string | null;
  repositoryId: string;
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
  metadata: Record<string, unknown> & {
    average_risk_score?: number;
    distribution_buckets?: {
      critical: number;
      high: number;
      low: number;
      moderate: number;
    };
    file_count?: number;
    filtered_by_path?: string | null;
    highest_risk_score?: number;
    include_tests?: boolean;
    language?: string | null;
    path_search?: string | null;
    single_file_breakdown?: {
      bugfix_count?: number;
      churn_commit_count?: number;
      complexity_score?: number;
      fan_in?: number;
      fan_out?: number;
      loc?: number;
    } | null;
    top_k?: number;
  };
  repository_id: string;
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
  repository_id: string;
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
  repository_id: string;
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
  repository_id: string;
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
  oauth_provider?: string | null;
  picture?: string | null;
};


export type ForgotPasswordRequest = {
  email: string;
};

export type ForgotPasswordResponse = {
  message: string;
  reset_url?: string;
};

export type ResetPasswordRequest = {
  new_password: string;
  token: string;
};

export type UserUpdateRequest = {
  current_password?: string | null;
  full_name?: string | null;
  password?: string | null;
};

export type FileSearchResult = {
  id: number;
  is_test: boolean;
  language: string;
  loc: number;
  path: string;
};

export type EvaluationRunListItem = {
  commit_limit: number;
  created_at: ISODateTime;
  evaluation_run_id: number;
  methods: string[];
  name: string;
  status: string;
};

export type ImpactRunListItem = {
  analysis_run_id: number;
  changed_files_count: number;
  created_at: ISODateTime;
  input_mode: string;
  status: string;
};

export type RefSearchResult = {
  commit_date: string | null;
  commit_message: string | null;
  commit_sha: string | null;
  name: string;
  ref_type: "branch" | "tag" | "commit" | string;
};


