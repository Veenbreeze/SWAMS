// The app's 4-color system (Material Design's Primary/Secondary/
// Background/Surface roles): primary for main actions, secondary as the
// recurring accent (input/chip outlines, the notifications indicator),
// background for every screen's base fill, surface for cards sitting on
// top of it. Every screen should use all 4 rather than falling back to
// plain white.
export const colors = {
  primary: "#2563eb",
  primaryPressed: "#1d4ed8",
  primaryForeground: "#ffffff",
  secondary: "#0d9488",
  secondaryPressed: "#0f766e",
  background: "#eaf2fb",
  surface: "#ffffff",
  text: "#111827",
  textMuted: "#6b7280",
  border: "#0d9488",
  surfaceMuted: "#f3f4f6",
  surfaceSubtle: "#f9fafb",
  danger: "#dc2626",
  success: "#059669",
  // Matches the web apps' validated status palette (see the dataviz-skill
  // note in frontend-*/src/index.css) so "present/late/absent" etc. read
  // the same way across mobile and web.
  cardBorder: "#e5e7eb",
};

// Attendance/leave status → accent color, mirroring the web apps'
// --status-good/warning/serious/critical tokens.
export const statusColors = {
  PRESENT: "#0ca30c",
  LATE: "#fab219",
  EARLY_DEPARTURE: "#ec835a",
  OVERTIME: "#2563eb",
  ABSENT: "#d03b3b",
  PENDING: "#fab219",
  APPROVED: "#0ca30c",
  REJECTED: "#d03b3b",
  CANCELLED: "#6b7280",
};
