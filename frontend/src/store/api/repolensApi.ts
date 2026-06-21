import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  EvaluationReportResponse,
  EvaluationRunRequest,
  EvaluationRunResponse,
  EvaluationStatusResponse,
  GraphResponse,
  HealthResponse,
  ImpactAnalyzeRequest,
  ImpactAnalyzeResponse,
  ImpactRunResponse,
  IndexRepositoryRequest,
  IndexRepositoryResponse,
  IndexStatusResponse,
  Repository,
  RepositoryCreate,
  RepositoryList,
  RepositoryRiskArgs,
  RepositoryRiskResponse,
  SemanticSearchRequest,
  SemanticSearchResponse,
  TestRecommendationRequest,
  TestRecommendationResponse,
} from "@/lib/api/types";

type ListRepositoriesArgs = {
  limit?: number;
  skip?: number;
};

type IndexRepositoryArgs = {
  body: IndexRepositoryRequest;
  repositoryId: number;
};

type GraphSubgraphArgs = {
  include_tests?: boolean;
  language?: string | null;
  max_nodes?: number;
  repositoryId: number;
};

type GraphNeighborsArgs = {
  fileId: number;
  repositoryId: number;
};

export const repolensApi = createApi({
  baseQuery: fetchBaseQuery({
    baseUrl: apiBaseUrl,
  }),
  endpoints: (builder) => ({
    createRepository: builder.mutation<Repository, RepositoryCreate>({
      invalidatesTags: ["Repository"],
      query: (body) => ({
        body,
        method: "POST",
        url: "/repositories",
      }),
    }),
    deleteRepository: builder.mutation<void, number>({
      invalidatesTags: ["Repository"],
      query: (repositoryId) => ({
        method: "DELETE",
        url: `/repositories/${repositoryId}`,
      }),
    }),
    getEvaluationReport: builder.query<EvaluationReportResponse, number>({
      providesTags: (_result, _error, evaluationRunId) => [
        { id: evaluationRunId, type: "Evaluation" },
      ],
      query: (evaluationRunId) => `/evaluation/${evaluationRunId}/report`,
    }),
    getEvaluationReportMarkdown: builder.query<string, number>({
      providesTags: (_result, _error, evaluationRunId) => [
        { id: evaluationRunId, type: "Evaluation" },
      ],
      query: (evaluationRunId) => ({
        responseHandler: "text",
        url: `/evaluation/${evaluationRunId}/report.md`,
      }),
    }),
    getEvaluationStatus: builder.query<EvaluationStatusResponse, number>({
      providesTags: (_result, _error, evaluationRunId) => [
        { id: evaluationRunId, type: "Evaluation" },
      ],
      query: (evaluationRunId) => `/evaluation/${evaluationRunId}`,
    }),
    getFileNeighbors: builder.query<GraphResponse, GraphNeighborsArgs>({
      providesTags: (_result, _error, { repositoryId }) => [
        { id: repositoryId, type: "Graph" },
      ],
      query: ({ fileId, repositoryId }) =>
        `/graph/repositories/${repositoryId}/file/${fileId}/neighbors`,
    }),
    getHealth: builder.query<HealthResponse, void>({
      query: () => "/health",
    }),
    getImpactRun: builder.query<ImpactRunResponse, number>({
      providesTags: (_result, _error, analysisRunId) => [
        { id: analysisRunId, type: "Impact" },
      ],
      query: (analysisRunId) => `/impact/runs/${analysisRunId}`,
    }),
    getIndexStatus: builder.query<IndexStatusResponse, number>({
      providesTags: (_result, _error, repositoryId) => [
        { id: repositoryId, type: "IndexStatus" },
      ],
      query: (repositoryId) => `/repositories/${repositoryId}/index/status`,
    }),
    getRepository: builder.query<Repository, number>({
      providesTags: (_result, _error, repositoryId) => [
        { id: repositoryId, type: "Repository" },
      ],
      query: (repositoryId) => `/repositories/${repositoryId}`,
    }),
    getRepositoryRisk: builder.query<RepositoryRiskResponse, RepositoryRiskArgs>({
      providesTags: (_result, _error, { repositoryId }) => [
        { id: repositoryId, type: "Risk" },
      ],
      query: ({ include_tests = false, language, repositoryId, top_k = 20 }) => ({
        params: {
          include_tests,
          language: language || undefined,
          top_k,
        },
        url: `/risk/repositories/${repositoryId}/files`,
      }),
    }),
    getRepositorySubgraph: builder.query<GraphResponse, GraphSubgraphArgs>({
      providesTags: (_result, _error, { repositoryId }) => [
        { id: repositoryId, type: "Graph" },
      ],
      query: ({ include_tests = true, language, max_nodes = 500, repositoryId }) => ({
        params: {
          include_tests,
          language: language || undefined,
          max_nodes,
        },
        url: `/graph/repositories/${repositoryId}/subgraph`,
      }),
    }),
    indexRepository: builder.mutation<IndexRepositoryResponse, IndexRepositoryArgs>({
      invalidatesTags: (_result, _error, { repositoryId }) => [
        { id: repositoryId, type: "IndexStatus" },
        { id: repositoryId, type: "Repository" },
      ],
      query: ({ body, repositoryId }) => ({
        body,
        method: "POST",
        url: `/repositories/${repositoryId}/index`,
      }),
    }),
    listRepositories: builder.query<RepositoryList, ListRepositoriesArgs | void>({
      providesTags: ["Repository"],
      query: (args) => ({
        params: {
          limit: args?.limit ?? 100,
          skip: args?.skip ?? 0,
        },
        url: "/repositories",
      }),
    }),
    recommendTests: builder.mutation<
      TestRecommendationResponse,
      TestRecommendationRequest
    >({
      query: (body) => ({
        body,
        method: "POST",
        url: "/tests/recommend",
      }),
    }),
    runEvaluation: builder.mutation<EvaluationRunResponse, EvaluationRunRequest>({
      invalidatesTags: ["Evaluation"],
      query: (body) => ({
        body,
        method: "POST",
        url: "/evaluation/run",
      }),
    }),
    runImpactAnalysis: builder.mutation<ImpactAnalyzeResponse, ImpactAnalyzeRequest>({
      invalidatesTags: ["Impact"],
      query: (body) => ({
        body,
        method: "POST",
        url: "/impact/analyze",
      }),
    }),
    semanticSearch: builder.mutation<SemanticSearchResponse, SemanticSearchRequest>({
      query: (body) => ({
        body,
        method: "POST",
        url: "/search/semantic",
      }),
    }),
  }),
  reducerPath: "repolensApi",
  tagTypes: ["Evaluation", "Graph", "Impact", "IndexStatus", "Repository", "Risk"],
});

export const {
  useCreateRepositoryMutation,
  useDeleteRepositoryMutation,
  useGetEvaluationReportMarkdownQuery,
  useGetEvaluationReportQuery,
  useGetEvaluationStatusQuery,
  useGetFileNeighborsQuery,
  useGetHealthQuery,
  useGetImpactRunQuery,
  useGetIndexStatusQuery,
  useGetRepositoryQuery,
  useGetRepositoryRiskQuery,
  useGetRepositorySubgraphQuery,
  useIndexRepositoryMutation,
  useListRepositoriesQuery,
  useRecommendTestsMutation,
  useRunEvaluationMutation,
  useRunImpactAnalysisMutation,
  useSemanticSearchMutation,
} = repolensApi;
