import apiClient from "@/api/client";

export function getMonthlyReport({ month }) {
  return apiClient.get("/reports/monthly", { params: { month } }).then((res) => res.data);
}

export function getWeeklyReport({ start }) {
  return apiClient.get("/reports/weekly", { params: { start } }).then((res) => res.data);
}

export function getLateReport(params) {
  return apiClient.get("/reports/late", { params }).then((res) => res.data);
}

export function getOvertimeReport(params) {
  return apiClient.get("/reports/overtime", { params }).then((res) => res.data);
}

// The export endpoint reads everything (`format`, plus report-specific
// params) from the query string, not a request body — see
// docs/03-API-SPECIFICATION.md §11's literal
// `POST /reports/{report}/export?format=pdf|xlsx` shape.
export function requestReportExport(reportType, params) {
  return apiClient
    .post(`/reports/${reportType}/export`, null, { params })
    .then((res) => res.data);
}

export function getExportJob(jobId) {
  return apiClient.get(`/reports/jobs/${jobId}`).then((res) => res.data);
}
