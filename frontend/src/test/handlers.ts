import { http, HttpResponse } from "msw";
import { apiBaseUrl } from "@/lib/api/client";
import type { HealthResponse, RepositoryList } from "@/lib/api/types";

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

export const handlers = [
  http.get(`${apiBaseUrl}/health`, () => HttpResponse.json(healthyResponse)),
  http.get(`${apiBaseUrl}/repositories`, () => HttpResponse.json(emptyRepositoryList)),
];
