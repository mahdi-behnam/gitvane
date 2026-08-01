"use client";

import { useEffect, useRef, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { apiBaseUrl } from "@/lib/api/client";
import type { IndexingProgressEvent } from "@/lib/api/types";

export type ConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "completed"
  | "error";

export interface UseIndexingSSEOptions {
  enabled: boolean;
  initialProgress?: IndexingProgressEvent | null;
  onComplete?: () => void;
  onError?: (error?: string) => void;
  repositoryId: string | number | null;
  token?: string | null;
}

export function useIndexingSSE({
  enabled,
  initialProgress = null,
  onComplete,
  onError,
  repositoryId,
  token,
}: UseIndexingSSEOptions) {
  const { notify } = useToast();
  const isIndexingStatus = (st?: string | null) =>
    Boolean(st && ["indexing", "indexing_queued", "queued", "cloning"].includes(st));

  const [progress, setProgress] = useState<IndexingProgressEvent | null>(() => {
    if (initialProgress && isIndexingStatus(initialProgress.status)) {
      return initialProgress;
    }
    if (enabled && repositoryId !== null && repositoryId !== "") {
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
        repository_id: String(repositoryId),
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
  const onErrorRef = useRef(onError);
  const prevEnabledRef = useRef(enabled);
  const isCompletedRef = useRef(false);
  const toastFiredRef = useRef<string | null>(null);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // When enabled transitions from false -> true (indexing started), initialize state
  useEffect(() => {
    const wasDisabled = !prevEnabledRef.current;
    prevEnabledRef.current = enabled;

    if (enabled && wasDisabled) {
      isCompletedRef.current = false;
      toastFiredRef.current = null;
      if (initialProgress && isIndexingStatus(initialProgress.status)) {
        setProgress(initialProgress);
      } else if (repositoryId !== null && repositoryId !== "") {
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
          repository_id: String(repositoryId),
          status: "indexing",
        });
      }
    }
  }, [enabled, initialProgress, repositoryId]);

  useEffect(() => {
    if (!enabled || repositoryId === null || repositoryId === "") {
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

          if (data.status === "indexed") {
            isCompletedRef.current = true;
            setConnectionState("completed");
            es.close();

            if (toastFiredRef.current !== "indexed") {
              toastFiredRef.current = "indexed";
              notify({
                title: "Indexing Complete",
                description: "Repository indexing completed successfully.",
                variant: "success",
              });
            }

            if (onCompleteRef.current) {
              onCompleteRef.current();
            }
          } else if (data.status === "index_failed") {
            isCompletedRef.current = true;
            setConnectionState("error");
            const errDetail = data.error || "Repository indexing failed.";
            setError(errDetail);
            es.close();

            if (toastFiredRef.current !== "index_failed") {
              toastFiredRef.current = "index_failed";
              notify({
                title: "Indexing Failed",
                description: errDetail,
                variant: "destructive",
              });
            }

            if (onErrorRef.current) {
              onErrorRef.current(errDetail);
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

        if (retryCountRef.current > 5) {
          setConnectionState("error");
          const msg = "Disconnected from repository indexing event stream.";
          setError(msg);
          if (toastFiredRef.current !== "stream_error") {
            toastFiredRef.current = "stream_error";
            notify({
              title: "Connection Lost",
              description: msg,
              variant: "destructive",
            });
          }
          if (onErrorRef.current) {
            onErrorRef.current(msg);
          }
          return;
        }

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
  }, [enabled, repositoryId, token, notify]);

  return {
    connectionState,
    error,
    progress,
  };
}
