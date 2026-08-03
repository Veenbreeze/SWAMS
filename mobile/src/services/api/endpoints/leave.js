import apiClient from "@/services/api/client";

export function getLeaveTypes() {
  return apiClient.get("/leave/types").then((res) => res.data.results ?? res.data);
}

export function getLeaveRequests() {
  return apiClient.get("/leave/requests").then((res) => res.data);
}

export function submitLeaveRequest({ leaveTypeId, startDate, endDate, reason }) {
  return apiClient
    .post("/leave/requests", {
      leave_type: leaveTypeId,
      start_date: startDate,
      end_date: endDate,
      reason,
    })
    .then((res) => res.data);
}

export function getLeaveBalance() {
  return apiClient.get("/leave/balance").then((res) => res.data);
}
