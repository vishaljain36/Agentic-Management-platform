"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export interface SSEStreamState {
  status: "IDLE" | "CONNECTING" | "STREAMING" | "CLOSED" | "ERROR";
  tokens: string[];
  assembledText: string;
  error: Error | null;
  start: () => void;
  stop: () => void;
}

export function useSSEStream(url?: string, autoStart: boolean = false) {
  const [status, setStatus] = useState<SSEStreamState["status"]>("IDLE");
  const [tokens, setTokens] = useState<string[]>([]);
  const [assembledText, setAssembledText] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const start = useCallback(() => {
    if (!url) return;
    if (esRef.current) {
      esRef.current.close();
    }

    setStatus("CONNECTING");
    setError(null);
    setTokens([]);
    setAssembledText("");

    try {
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setStatus("STREAMING");
      };

      const handleChunk = (rawText: string) => {
        try {
          const parsed = JSON.parse(rawText);
          const chunk = parsed.token ?? parsed.delta ?? "";
          if (chunk) {
            setTokens((prev) => [...prev, chunk]);
            setAssembledText((prev) => prev + chunk);
          }
        } catch {
          if (rawText) {
            setTokens((prev) => [...prev, rawText]);
            setAssembledText((prev) => prev + rawText);
          }
        }
      };

      es.onmessage = (event) => {
        handleChunk(event.data);
      };

      es.addEventListener("token_delta", (event: any) => {
        handleChunk(event.data);
      });

      const handleClose = () => {
        setStatus("CLOSED");
        if (esRef.current) {
          esRef.current.close();
          esRef.current = null;
        }
      };

      es.addEventListener("end", handleClose);
      es.addEventListener("close", handleClose);
      es.addEventListener("run_complete", handleClose);

      es.onerror = () => {
        // If already closed, don't mark as error
        if (es.readyState === 2) {
          setStatus("CLOSED");
        } else {
          setStatus("ERROR");
          setError(new Error("EventSource connection error"));
        }
        es.close();
      };
    } catch (e: any) {
      setStatus("ERROR");
      setError(e);
    }
  }, [url]);

  const stop = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setStatus("CLOSED");
  }, []);

  useEffect(() => {
    if (autoStart && url) {
      start();
    }
    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [autoStart, url, start]);

  return {
    status,
    tokens,
    assembledText,
    error,
    start,
    stop,
  };
}

