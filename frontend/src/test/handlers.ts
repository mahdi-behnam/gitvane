import { http, HttpResponse } from "msw";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  EvaluationReportResponse,
  EvaluationRunResponse,
  EvaluationStatusResponse,
  GraphResponse,
  HealthResponse,
  ImpactAnalyzeResponse,
  ImpactRunResponse,
  IndexRepositoryResponse,
  IndexStatusResponse,
  Repository,
  RepositoryList,
  RepositoryRiskResponse,
  SemanticSearchResponse,
  TestRecommendationResponse,
} from "@/lib/api/types";
import type { ApiKeyCreatedResponse, ApiKeyItem } from "@/types/apiKeys";

const emptyRepositoryList: RepositoryList = {
  items: [],
  limit: 100,
  skip: 0,
  total: 0,
};

const healthyResponse: HealthResponse = {
  database: "connected",
  status: "healthy",
};

const repositoryFixture: Repository = {
  clone_url: "https://github.com/mahdi-behnam/gitvane.git",
  created_at: "2026-06-21T10:00:00Z",
  current_ref: "main",
  default_branch: "main",
  id: "77777777-7777-7777-7777-777777777777",
  indexed_at: "2026-06-21T10:30:00Z",
  last_indexed_commit: "abc123",
  name: "gitvane",
  repo_metadata: null,
  status: "indexed",
  updated_at: "2026-06-21T10:30:00Z",
};

const indexStatusFixture: IndexStatusResponse = {
  chunk_count: 30,
  commit_count: 5,
  current_ref: "main",
  dependency_edge_count: 12,
  file_count: 18,
  indexed_at: "2026-06-21T10:30:00Z",
  last_indexed_commit: "abc123",
  repository_id: "77777777-7777-7777-7777-777777777777",
  status: "indexed",
  symbol_count: 44,
};

const graphFixture: GraphResponse = {
  edges: [
    {
      confidence: 0.86,
      edge_type: "imports",
      evidence: { import: "IndexingService" },
      id: 31,
      source_file_id: 1,
      source_path: "backend/app/api/v1/endpoints/indexing.py",
      target_file_id: 2,
      target_path: "backend/app/services/indexing_service.py",
    },
  ],
  nodes: [
    {
      id: 1,
      is_generated: false,
      is_test: false,
      language: "python",
      loc: 80,
      path: "backend/app/api/v1/endpoints/indexing.py",
    },
    {
      id: 2,
      is_generated: false,
      is_test: false,
      language: "python",
      loc: 240,
      path: "backend/app/services/indexing_service.py",
    },
  ],
  repository_id: "77777777-7777-7777-7777-777777777777",
};

const riskFixture: RepositoryRiskResponse = {
  files: [
    {
      components: { dependency: 0.8 },
      path: "backend/app/services/indexing_service.py",
      reasons: ["High dependency fan-in."],
      risk_score: 0.82,
    },
  ],
  metadata: {},
  repository_id: "77777777-7777-7777-7777-777777777777",
};

const impactFixture: ImpactAnalyzeResponse = {
  analysis_run_id: 91,
  base_ref: null,
  changed_files: [{ path: "backend/app/services/indexing_service.py" }],
  changed_symbols: [],
  head_ref: null,
  impacted_files: [],
  llm_explanation: null,
  recommended_tests: [],
  repository_id: "77777777-7777-7777-7777-777777777777",
  risk_summary: { highest_risk_files: [] },
};

const evaluationStatusFixture: EvaluationStatusResponse = {
  commit_limit: 50,
  error_message: null,
  evaluation_run_id: 42,
  methods: ["hybrid"],
  name: "Repository evaluation",
  repository_id: "77777777-7777-7777-7777-777777777777",
  status: "completed",
  summary: { hybrid: { map: 0.62 } },
};

export const handlers = [
  http.post(`${apiBaseUrl}/auth/refresh`, () =>
    HttpResponse.json({
      access_token: "mock-access-token",
      token_type: "bearer",
    }),
  ),
  http.post(`${apiBaseUrl}/auth/logout`, () =>
    HttpResponse.json({
      status: "success",
    }),
  ),
  http.get(`${apiBaseUrl}/auth/me`, () =>
    HttpResponse.json({
      id: 1,
      email: "user@example.com",
      full_name: "Test User",
      is_active: true,
      created_at: "2026-06-21T10:00:00Z",
      updated_at: "2026-06-21T10:00:00Z",
    }),
  ),
  http.put(`${apiBaseUrl}/auth/me`, async ({ request }) => {
    const body = (await request.json()) as { current_password?: string; full_name?: string; password?: string };
    if (body.password && !body.current_password) {
      return HttpResponse.json({ detail: "Current password is required to change password" }, { status: 400 });
    }
    return HttpResponse.json({
      id: 1,
      email: "user@example.com",
      full_name: body.full_name || "Test User",
      is_active: true,
      created_at: "2026-06-21T10:00:00Z",
      updated_at: "2026-06-21T10:00:00Z",
    });
  }),
  http.post(`${apiBaseUrl}/auth/forgot-password`, async ({ request }) => {
    const body = (await request.json()) as { email: string };
    return HttpResponse.json({
      message: "Password reset email sent (dev mode)",
      reset_url: `${process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"}/reset-password?token=mocked-token-for-${encodeURIComponent(body.email)}`,
    });
  }),
  http.post(`${apiBaseUrl}/auth/reset-password`, () =>
    HttpResponse.json({
      status: "success",
      message: "Password reset successfully",
    }),
  ),
  http.get(`${apiBaseUrl}/health`, () => HttpResponse.json(healthyResponse)),
  http.get(`${apiBaseUrl}/repositories`, () => HttpResponse.json(emptyRepositoryList)),
  http.post(`${apiBaseUrl}/repositories/remote-branches`, () =>
    HttpResponse.json({
      branches: [
        {
          commit_date: null,
          commit_message: null,
          commit_sha: "abc1234",
          name: "main",
          ref_type: "branch",
        },
        {
          commit_date: null,
          commit_message: null,
          commit_sha: "def5678",
          name: "develop",
          ref_type: "branch",
        },
      ],
      default_branch: "main",
    }),
  ),
  http.post(`${apiBaseUrl}/repositories`, () => HttpResponse.json(repositoryFixture)),
  http.get(`${apiBaseUrl}/repositories/:repositoryId`, () =>
    HttpResponse.json(repositoryFixture),
  ),
  http.delete(`${apiBaseUrl}/repositories/:repositoryId`, () =>
    HttpResponse.json(null),
  ),
  http.post(`${apiBaseUrl}/repositories/:repositoryId/index`, () => {
    const response: IndexRepositoryResponse = {
      chunks_indexed: 30,
      commits_indexed: 5,
      current_ref: "main",
      dependency_edges_indexed: 12,
      embeddings_indexed: 30,
      files_indexed: 18,
      files_skipped: 0,
      indexed_at: "2026-06-21T10:30:00Z",
      parser_errors: [],
      repository_id: "77777777-7777-7777-7777-777777777777",
      status: "indexed",
      symbols_indexed: 44,
      warnings: [],
    };

    return HttpResponse.json(response);
  }),
  http.post(`${apiBaseUrl}/repositories/:repositoryId/sync`, () => {
    const response: IndexRepositoryResponse = {
      chunks_indexed: 30,
      commits_indexed: 5,
      current_ref: "main",
      dependency_edges_indexed: 12,
      embeddings_indexed: 30,
      files_indexed: 18,
      files_skipped: 0,
      indexed_at: "2026-06-21T10:30:00Z",
      parser_errors: [],
      repository_id: "77777777-7777-7777-7777-777777777777",
      status: "indexed",
      symbols_indexed: 44,
      warnings: [],
    };

    return HttpResponse.json(response);
  }),
  http.get(`${apiBaseUrl}/repositories/:repositoryId/index/status`, () =>
    HttpResponse.json(indexStatusFixture),
  ),
  http.get(`${apiBaseUrl}/repositories/:repositoryId/files/search`, () =>
    HttpResponse.json([
      {
        id: "1",
        is_test: false,
        language: "python",
        loc: 50,
        path: "backend/app/api/v1/endpoints/indexing.py",
      },
      {
        id: "2",
        is_test: false,
        language: "python",
        loc: 100,
        path: "backend/app/services/indexing_service.py",
      },
    ]),
  ),
  http.get(`${apiBaseUrl}/repositories/:repositoryId/languages`, () =>
    HttpResponse.json(["python", "typescript", "markdown"]),
  ),
  http.get(`${apiBaseUrl}/impact/repository/:repositoryId/runs`, () =>
    HttpResponse.json([
      {
        analysis_run_id: 91,
        created_at: "2026-06-21T10:00:00Z",
        input_mode: "changed_files",
        status: "completed",
      },
    ]),
  ),
  http.get(`${apiBaseUrl}/evaluation/repository/:repositoryId/runs`, () =>
    HttpResponse.json([
      {
        created_at: "2026-06-21T10:00:00Z",
        evaluation_run_id: 42,
        name: "Nightly quality check",
        status: "completed",
      },
    ]),
  ),
  http.post(`${apiBaseUrl}/search/semantic`, () => {
    const response: SemanticSearchResponse = { results: [] };

    return HttpResponse.json(response);
  }),
  http.post(`${apiBaseUrl}/impact/analyze`, () => HttpResponse.json(impactFixture)),
  http.get(`${apiBaseUrl}/impact/runs/:analysisRunId`, () => {
    const response: ImpactRunResponse = {
      analysis_run_id: 91,
      changed_files: impactFixture.changed_files,
      changed_symbols: [],
      input_mode: "changed_files",
      predictions: [],
      repository_id: "77777777-7777-7777-7777-777777777777",
      status: "completed",
    };

    return HttpResponse.json(response);
  }),
  http.post(`${apiBaseUrl}/tests/recommend`, () => {
    const response: TestRecommendationResponse = {
      changed_files: [{ path: "backend/app/services/indexing_service.py" }],
      recommended_tests: [],
      repository_id: "77777777-7777-7777-7777-777777777777",
    };

    return HttpResponse.json(response);
  }),
  http.get(`${apiBaseUrl}/risk/repositories/:repositoryId/files`, () =>
    HttpResponse.json(riskFixture),
  ),
  http.get(`${apiBaseUrl}/graph/repositories/:repositoryId/subgraph`, () =>
    HttpResponse.json(graphFixture),
  ),
  http.get(
    `${apiBaseUrl}/graph/repositories/:repositoryId/file/:fileId/neighbors`,
    () => HttpResponse.json(graphFixture),
  ),
  http.post(`${apiBaseUrl}/evaluation/run`, () => {
    const response: EvaluationRunResponse = {
      evaluation_run_id: 42,
      status: "completed",
      summary: evaluationStatusFixture.summary,
    };

    return HttpResponse.json(response);
  }),
  http.get(`${apiBaseUrl}/evaluation/:evaluationRunId`, () =>
    HttpResponse.json(evaluationStatusFixture),
  ),
  http.get(`${apiBaseUrl}/evaluation/:evaluationRunId/report`, () => {
    const response: EvaluationReportResponse = {
      evaluation_run_id: 42,
      markdown: "# Evaluation Report",
    };

    return HttpResponse.json(response);
  }),
  http.get(`${apiBaseUrl}/evaluation/:evaluationRunId/report.md`, () =>
    HttpResponse.text("# Evaluation Report"),
  ),
  http.get(`${apiBaseUrl}/api-keys`, () => {
    const keys: ApiKeyItem[] = [
      {
        created_at: "2026-06-21T10:00:00Z",
        expires_at: null,
        id: "key-123",
        is_revoked: false,
        last_used_at: "2026-06-21T11:00:00Z",
        name: "Cursor IDE",
        key_prefix: "gv_live_abc12345",
      },
    ];
    return HttpResponse.json(keys);
  }),
  http.post(`${apiBaseUrl}/api-keys`, async ({ request }) => {
    const body = (await request.json()) as { expires_in_days?: number; name: string };
    const response: ApiKeyCreatedResponse = {
      created_at: "2026-06-21T10:00:00Z",
      expires_at: body.expires_in_days ? "2026-07-21T10:00:00Z" : null,
      id: "key-new",
      is_revoked: false,
      last_used_at: null,
      name: body.name,
      key_prefix: "gv_live_xyz98765",
      raw_key: "gv_live_xyz9876543210abcdef",
    };
    return HttpResponse.json(response);
  }),
  http.delete(`${apiBaseUrl}/api-keys/:id`, () =>
    HttpResponse.json(null),
  ),
];
