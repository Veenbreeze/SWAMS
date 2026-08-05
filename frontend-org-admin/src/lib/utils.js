import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

function humanizeFieldName(field) {
  return field.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

// apiClient rejects with the backend's {code, message, details} error
// object (see api/client.js) — `message` alone is often a generic
// "Validation failed." for field-level errors (missing/too-short
// fields, password strength, etc.), while the actually-useful text is
// in `details`, keyed by field name. Prefixing each message with its
// field matters whenever a form has more than one field of the same
// kind (e.g. organization email vs admin email) — without it, "Enter a
// valid email address" doesn't say which box to fix.
export function formatApiError(err, fallback) {
  const details = err?.details;
  if (details && typeof details === "object") {
    const entries = Object.entries(details).filter(([, messages]) =>
      Array.isArray(messages) ? messages.length > 0 : Boolean(messages)
    );
    if (entries.length > 0) {
      return entries
        .map(([field, messages]) => {
          const text = Array.isArray(messages) ? messages.join(" ") : messages;
          return field === "non_field_errors" ? text : `${humanizeFieldName(field)}: ${text}`;
        })
        .join(" ");
    }
  }
  return err?.message || fallback;
}
