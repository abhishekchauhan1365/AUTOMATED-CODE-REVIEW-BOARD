import { useEffect, useRef, useState } from "react";
import { fetchReviewStatus } from "../services/api";
import type { ExecutionEvent, ReviewStatusResponse } from "../types/review";

export function useReviewStream(reviewId: string | undefined) {
  const [status, setStatus] = useState<ReviewStatusResponse | null>(null);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const doneRef = useRef(false);

  useEffect(() => {
    if (!reviewId) return;
    doneRef.current = false;
    setEvents([]);
    setError(null);

    let active = true;
    let pollTimer: number | undefined;
    let source: EventSource | null = null;

    const loadStatus = async () => {
      try {
        const s = await fetchReviewStatus(reviewId);
        if (!active) return;
        setStatus(s);
        if (s.overall_status === "completed" || s.overall_status === "failed") {
          doneRef.current = true;
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load status");
      }
    };

    void loadStatus();

    try {
      source = new EventSource(`/api/reviews/${reviewId}/events`);
      source.onmessage = (msg) => {
        if (!active) return;
        try {
          const parsed = JSON.parse(msg.data) as {
            type?: string;
            status?: ReviewStatusResponse;
            event?: ExecutionEvent;
          };
          if (parsed.status) {
            setStatus(parsed.status);
          }
          if (parsed.event) {
            setEvents((prev) => {
              const key = `${parsed.event!.timestamp}-${parsed.event!.agent_name}-${parsed.event!.event}`;
              if (prev.some((e) => `${e.timestamp}-${e.agent_name}-${e.event}` === key)) {
                return prev;
              }
              return [...prev, parsed.event!];
            });
          }
          if (parsed.type === "workflow_done") {
            doneRef.current = true;
            source?.close();
          }
        } catch {
          // ignore malformed SSE chunk
        }
      };
      source.onerror = () => {
        source?.close();
      };
    } catch {
      // Fallback to polling below
    }

    pollTimer = window.setInterval(() => {
      if (!doneRef.current) {
        void loadStatus();
      } else if (pollTimer) {
        window.clearInterval(pollTimer);
      }
    }, 1000);

    return () => {
      active = false;
      source?.close();
      if (pollTimer) window.clearInterval(pollTimer);
    };
  }, [reviewId]);

  return { status, events, error };
}

