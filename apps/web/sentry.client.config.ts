// Sentry Client Configuration for Next.js 15 Edge & Client Components
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN || "";

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    tracesSampleRate: 1.0,
    debug: process.env.NODE_ENV === "development",
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    // Filter and tag real-time streaming issues
    beforeSend(event, hint) {
      if (hint.originalException) {
        const errorText = String(hint.originalException).toLowerCase();
        if (
          errorText.includes("websocket") ||
          errorText.includes("eventsource") ||
          errorText.includes("sse") ||
          errorText.includes("connection closed")
        ) {
          event.tags = {
            ...event.tags,
            subsystem: "realtime_streaming",
            connection_failure: "true",
          };
          event.level = "warning";
        }
      }
      return event;
    },
  });
}

/**
 * Capture client-side streaming or canvas rendering errors with custom context.
 */
export function captureClientError(error: unknown, context?: Record<string, unknown>): void {
  if (SENTRY_DSN) {
    Sentry.captureException(error, { extra: context });
  } else {
    console.error("[Sentry Client Observability]", error, context);
  }
}

export default Sentry;

