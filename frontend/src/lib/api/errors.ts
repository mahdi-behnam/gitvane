import type { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import type { SerializedError } from "@reduxjs/toolkit";

export type ApiErrorKind = "offline" | "validation" | "notFound" | "server" | "unknown";

export type NormalizedApiError = {
  detail?: unknown;
  kind: ApiErrorKind;
  message: string;
  status?: number | string;
};

function detailToMessage(detail: unknown) {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" && item && "msg" in item
          ? String(item.msg)
          : "Validation error",
      )
      .join("; ");
  }

  return undefined;
}

export function normalizeApiError(
  error: FetchBaseQueryError | SerializedError | undefined,
): NormalizedApiError {
  if (!error) {
    return { kind: "unknown", message: "Unexpected error" };
  }

  if ("status" in error) {
    if (error.status === "FETCH_ERROR") {
      return {
        kind: "offline",
        message: "The service is offline or unreachable.",
        status: error.status,
      };
    }

    if (error.status === "PARSING_ERROR" || error.status === "TIMEOUT_ERROR") {
      return {
        kind: "unknown",
        message: "The response could not be read.",
        status: error.status,
      };
    }

    const status = Number(error.status);
    const data =
      typeof error.data === "object" && error.data !== null
        ? (error.data as { detail?: unknown })
        : undefined;
    const message = detailToMessage(data?.detail);

    if (status === 400 || status === 422) {
      return {
        detail: data?.detail,
        kind: "validation",
        message: message ?? "The request was not valid.",
        status,
      };
    }

    if (status === 404) {
      return {
        detail: data?.detail,
        kind: "notFound",
        message: message ?? "The requested resource was not found.",
        status,
      };
    }

    if (status >= 500) {
      return {
        detail: data?.detail,
        kind: "server",
        message: "An unexpected error occurred.",
        status,
      };
    }

    return {
      detail: data?.detail,
      kind: "unknown",
      message: message ?? "The request failed.",
      status,
    };
  }

  return {
    kind: "unknown",
    message: error.message ?? "Unexpected error",
  };
}
