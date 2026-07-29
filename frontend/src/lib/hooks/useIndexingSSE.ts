"use client";

import { useEffect, useRef, useState } from "react";
import { apiBaseUrl } from "@/lib/api/client";
import type { IndexingProgressEvent } from "@/lib/api/types";

export type ConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "completed"
  | "error";

interface UseIndexingSSEOptions {
  enabled: boolean;
  initialProgress?: IndexingProgressEvent | null;
  onComplete?: () => void;
  repositoryId: number | null;
  token?: string | null;
}

export function useIndexingSSE({
  enabled,
  initialProgress = null,
  onComplete,
  repositoryId,
  token,
}: UseIndexingSSEOptions) {
  const [progress, setProgress] = useState<IndexingProgressEvent | null>(() => {
    if (initialProgress && initialProgress.status === "indexing") {
      return initialProgress;
    }
    if (enabled) {
      return {
        chunks_processed: 0,
        chunks_total: 0,
        error: null,
        estimated_seconds_remaining: null,
        files_processed: 0,
        files_total: 0,
        phase: "parsing",
        phase_name: "Phase 1/4: Discovering & Parsing Files",
        progress_percentage: 0.0,
        repository_id: repositoryId ?? 0,
        status: "indexing",
      };
    }
    return initialProgress;
  });

  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [error, setError] = useState<string | null>(null);

  const retryCountRef = useRef(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const onCompleteRef = useRef(onComplete);
  const prevEnabledRef = useRef(enabled);
  const isCompletedRef = useRef(false);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // When enabled transitions from false -> true (indexing started), initialize 0% state for new run
  useEffect(() => {
    const wasDisabled = !prevEnabledRef.current;
    prevEnabledRef.current = enabled;

    if (enabled && wasDisabled) {
      isCompletedRef.current = false;
      if (initialProgress && initialProgress.status === "indexing") {
        setProgress(initialProgress);
      } else {
        setProgress({
          chunks_processed: 0,
          chunks_total: 0,
          error: null,
          estimated_seconds_remaining: null,
          files_processed: 0,
          files_total: 0,
          phase: "parsing",
          phase_name: "Phase 1/4: Discovering & Parsing Files",
          progress_percentage: 0.0,
          repository_id: repositoryId ?? 0,
          status: "indexing",
        });
      }
    }
  }, [enabled, initialProgress, repositoryId]);

  useEffect(() => {
    if (!enabled || !repositoryId) {
      setConnectionState("idle");
      return;
    }

    let isSubscribed = true;

    const connect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      setConnectionState((prev) =>
        prev === "idle" || prev === "connecting" ? "connecting" : "reconnecting"
      );

      const sseUrl = token
        ? `${apiBaseUrl}/repositories/${repositoryId}/index/events?token=${encodeURIComponent(
            token
          )}`
        : `${apiBaseUrl}/repositories/${repositoryId}/index/events`;

      const es = new EventSource(sseUrl, { withCredentials: true });
      eventSourceRef.current = es;

      es.onopen = () => {
        if (!isSubscribed) return;
        retryCountRef.current = 0;
        setConnectionState("connected");
        setError(null);
      };

      const handleMessage = (event: MessageEvent) => {
        if (!isSubscribed || !event.data || event.data.startsWith(":")) return;
        try {
          const data: IndexingProgressEvent = JSON.parse(event.data);
          setProgress(data);

          if (data.status === "indexed" || data.status === "index_failed") {
            isCompletedRef.current = true;
            setConnectionState(data.status === "indexed" ? "completed" : "error");
            es.close();
            if (data.status === "indexed" && onCompleteRef.current) {
              onCompleteRef.current();
            }
          }
        } catch (err) {
          console.error("Failed to parse SSE progress event", err);
        }
      };

      es.onmessage = handleMessage;
      es.addEventListener("progress", handleMessage);

      es.onerror = () => {
        if (!isSubscribed || isCompletedRef.current) return;
        es.close();

        retryCountRef.current += 1;
        setConnectionState("reconnecting");

        // Exponential backoff with jitter up to 15 seconds
        const delay = Math.min(
          15000,
          Math.pow(2, retryCountRef.current) * 1000 + Math.random() * 1000
        );

        reconnectTimerRef.current = setTimeout(() => {
          if (isSubscribed) {
            connect();
          }
        }, delay);
      };
    };

    connect();

    return () => {
      isSubscribed = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [enabled, repositoryId, token]);

  return {
    connectionState,
    error,
    progress,
  };
}
