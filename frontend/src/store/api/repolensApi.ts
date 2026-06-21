import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  HealthResponse,
  IndexRepositoryRequest,
  IndexRepositoryResponse,
  IndexStatusResponse,
  Repository,
  RepositoryCreate,
  RepositoryList,
} from "@/lib/api/types";

type ListRepositoriesArgs = {
  limit?: number;
  skip?: number;
};

type IndexRepositoryArgs = {
  body: IndexRepositoryRequest;
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
    getHealth: builder.query<HealthResponse, void>({
      query: () => "/health",
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
  }),
  reducerPath: "repolensApi",
  tagTypes: ["IndexStatus", "Repository"],
});

export const {
  useCreateRepositoryMutation,
  useDeleteRepositoryMutation,
  useGetHealthQuery,
  useGetIndexStatusQuery,
  useGetRepositoryQuery,
  useIndexRepositoryMutation,
  useListRepositoriesQuery,
} = repolensApi;
