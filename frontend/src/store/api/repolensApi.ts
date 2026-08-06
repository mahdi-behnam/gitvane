import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { apiBaseUrl } from "@/lib/api/client";
import { setCredentials, clearCredentials } from "@/store/slices/authSlice";
import type {
  EvaluationReportResponse,
  EvaluationRunListItem,
  EvaluationRunRequest,
  EvaluationRunResponse,
  EvaluationStatusResponse,
  FileSearchResult,
  GraphResponse,
  HealthResponse,
  ImpactAnalyzeRequest,
  ImpactAnalyzeResponse,
  ImpactRunListItem,
  ImpactRunResponse,
  IndexRepositoryRequest,
  IndexRepositoryResponse,
  IndexStatusResponse,
  RefSearchResult,
  Repository,
  RepositoryCreate,
  RepositoryList,
  RepositoryRiskArgs,
  RepositoryRiskResponse,
  SemanticSearchRequest,
  SemanticSearchResponse,
  TestRecommendationRequest,
  TestRecommendationResponse,
  UserCreate,
  LoginRequest,
  TokenResponse,
  UserResponse,
} from "@/lib/api/types";

type ListRepositoriesArgs = {
  limit?: number;
  skip?: number;
};

type IndexRepositoryArgs = {
  body: IndexRepositoryRequest;
  repositoryId: string;
};

type GraphSubgraphArgs = {
  include_tests?: boolean;
  language?: string | null;
  max_nodes?: number;
  repositoryId: string;
};

type GraphNeighborsArgs = {
  fileId: number;
  repositoryId: string;
};

const rawBaseQuery = fetchBaseQuery({
  baseUrl: apiBaseUrl,
  credentials: "include",
  prepareHeaders: (headers, { getState }) => {
    const state = getState() as { auth?: { accessToken: string | null } };
    const token = state.auth?.accessToken;
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
  },
});

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift();
  return undefined;
}

const baseQuery: typeof rawBaseQuery = async (args, api, extraOptions) => {
  const adjustedArgs = typeof args === "string" ? { url: args } : { ...args };

  if (!adjustedArgs.credentials) {
    adjustedArgs.credentials = "include";
  }

  // Inject CSRF token for state-changing requests or refresh/logout requests
  const method = adjustedArgs.method?.toUpperCase() || "GET";
  const isStateChanging = !["GET", "HEAD", "OPTIONS"].includes(method);
  const isRefreshOrLogout =
    adjustedArgs.url?.includes("/auth/refresh") ||
    adjustedArgs.url?.includes("/auth/logout");

  if (isStateChanging || isRefreshOrLogout) {
    const csrfToken = getCookie("csrf_token");
    if (csrfToken) {
      const headers = new Headers();
      if (adjustedArgs.headers) {
        const rawHeaders = adjustedArgs.headers;
        if (rawHeaders instanceof Headers) {
          rawHeaders.forEach((val, key) => headers.set(key, val));
        } else if (Array.isArray(rawHeaders)) {
          for (const pair of rawHeaders) {
            if (pair[0] && pair[1]) {
              headers.set(pair[0], pair[1]);
            }
          }
        } else {
          for (const key of Object.keys(rawHeaders)) {
            const val = (rawHeaders as Record<string, string | undefined>)[key];
            if (val !== undefined) {
              headers.set(key, val);
            }
          }
        }
      }
      headers.set("X-CSRF-Token", csrfToken);
      adjustedArgs.headers = headers;
    }
  }

  return rawBaseQuery(adjustedArgs, api, extraOptions);
};

let refreshPromise: Promise<TokenResponse | null> | null = null;

const baseQueryWithReauth: typeof rawBaseQuery = async (args, api, extraOptions) => {
  let result = await baseQuery(args, api, extraOptions);

  const url = typeof args === "string" ? args : args.url;
  const isAuthEndpoint =
    url?.includes("/auth/login") ||
    url?.includes("/auth/refresh") ||
    url?.includes("/auth/logout") ||
    url?.includes("/auth/forgot-password") ||
    url?.includes("/auth/reset-password");

  if (result.error && result.error.status === 401 && !isAuthEndpoint) {
    if (!refreshPromise) {
      refreshPromise = (async () => {
        try {
          const refreshResult = await baseQuery(
            { url: "/auth/refresh", method: "POST" },
            api,
            extraOptions
          );

          if (refreshResult.data) {
            const data = refreshResult.data as TokenResponse;
            api.dispatch(setCredentials({ accessToken: data.access_token }));
            return data;
          } else {
            api.dispatch(clearCredentials());
            if (typeof document !== "undefined") {
              document.cookie =
                "repolens_logged_in=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
            }
            return null;
          }
        } catch {
          api.dispatch(clearCredentials());
          return null;
        } finally {
          refreshPromise = null;
        }
      })();
    }

    const refreshResult = await refreshPromise;

    if (refreshResult) {
      result = await baseQuery(args, api, extraOptions);
    }
  }

  return result;
};

export const repolensApi = createApi({
  baseQuery: baseQueryWithReauth,
  endpoints: (builder) => ({
    createRepository: builder.mutation<Repository, RepositoryCreate>({
      invalidatesTags: ["Repository"],
      query: (body) => ({
        body,
        method: "POST",
        url: "/repositories",
      }),
    }),
    deleteRepository: builder.mutation<void, string>({
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
    getIndexStatus: builder.query<IndexStatusResponse, string>({
      providesTags: (_result, _error, repositoryId) => [
        { id: repositoryId, type: "IndexStatus" },
      ],
      query: (repositoryId) => `/repositories/${repositoryId}/index/status`,
    }),
    getRepository: builder.query<Repository, string>({
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
        "Repository",
      ],
      query: ({ body, repositoryId }) => ({
        body,
        method: "POST",
        url: `/repositories/${repositoryId}/index`,
      }),
    }),
    listRepositories: builder.query<RepositoryList, ListRepositoriesArgs | void>({
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: "Repository" as const, id })),
              "Repository",
            ]
          : ["Repository"],
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
    signup: builder.mutation<TokenResponse, UserCreate>({
      query: (body) => ({
        body,
        method: "POST",
        url: "/auth/signup",
      }),
    }),
    login: builder.mutation<TokenResponse, LoginRequest>({
      query: (body) => ({
        body,
        method: "POST",
        url: "/auth/login",
      }),
    }),
    logout: builder.mutation<{ status: string; message: string }, void>({
      query: () => ({
        method: "POST",
        url: "/auth/logout",
      }),
    }),
    refresh: builder.mutation<TokenResponse, void>({
      query: () => ({
        method: "POST",
        url: "/auth/refresh",
      }),
    }),
    me: builder.query<UserResponse, void>({
      query: () => "/auth/me",
      providesTags: ["User"],
    }),
    forgotPassword: builder.mutation<
      { message: string; reset_url?: string },
      { email: string }
    >({
      query: (body) => ({
        body,
        method: "POST",
        url: "/auth/forgot-password",
      }),
    }),
    resetPassword: builder.mutation<
      { status: string; message: string },
      { new_password: string; token: string }
    >({
      query: (body) => ({
        body,
        method: "POST",
        url: "/auth/reset-password",
      }),
    }),
    updateMe: builder.mutation<
      UserResponse,
      { current_password?: string; full_name?: string; password?: string }
    >({
      query: (body) => ({
        body,
        method: "PUT",
        url: "/auth/me",
      }),
      invalidatesTags: ["User"],
    }),
    getRepositoryLanguages: builder.query<string[], string>({
      query: (repositoryId) => `/repositories/${repositoryId}/languages`,
      providesTags: ["Repository"],
    }),
    searchRepositoryFiles: builder.query<
      FileSearchResult[],
      { limit?: number; query?: string; repositoryId: string }
    >({
      query: ({ limit = 50, query = "", repositoryId }) =>
        `/repositories/${repositoryId}/files/search?query=${encodeURIComponent(query)}&limit=${limit}`,
      providesTags: ["Repository"],
    }),
    searchRepositoryRefs: builder.query<
      RefSearchResult[],
      { limit?: number; query?: string; ref_type?: string; repositoryId: string }
    >({
      query: ({ limit = 50, query = "", ref_type, repositoryId }) => {
        let url = `/repositories/${repositoryId}/refs?query=${encodeURIComponent(query)}&limit=${limit}`;
        if (ref_type) {
          url += `&ref_type=${encodeURIComponent(ref_type)}`;
        }
        return url;
      },
      providesTags: ["Repository"],
    }),
    listEvaluationRuns: builder.query<EvaluationRunListItem[], string>({
      query: (repositoryId) => `/evaluation/repository/${repositoryId}/runs`,
      providesTags: ["Evaluation"],
    }),
    listImpactRuns: builder.query<ImpactRunListItem[], string>({
      query: (repositoryId) => `/impact/repository/${repositoryId}/runs`,
      providesTags: ["Impact"],
    }),
  }),
  reducerPath: "repolensApi",
  tagTypes: ["Evaluation", "Graph", "Impact", "IndexStatus", "Repository", "Risk", "User"],
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
  useLazyGetImpactRunQuery,
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
  useSignupMutation,
  useLoginMutation,
  useLogoutMutation,
  useRefreshMutation,
  useMeQuery,
  useLazyMeQuery,
  useForgotPasswordMutation,
  useResetPasswordMutation,
  useUpdateMeMutation,
  useGetRepositoryLanguagesQuery,
  useSearchRepositoryFilesQuery,
  useLazySearchRepositoryFilesQuery,
  useSearchRepositoryRefsQuery,
  useLazySearchRepositoryRefsQuery,
  useListEvaluationRunsQuery,
  useListImpactRunsQuery,
} = repolensApi;

