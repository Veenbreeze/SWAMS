import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LeaveList from "@/pages/leaves/LeaveList";

vi.mock("@/api/endpoints/leave", () => ({
  getLeaveRequests: vi.fn(),
  approveLeaveRequest: vi.fn(),
  rejectLeaveRequest: vi.fn(),
  getLeaveBalance: vi.fn(),
}));

import { getLeaveRequests } from "@/api/endpoints/leave";

const PENDING_REQUEST = {
  id: "11111111-1111-1111-1111-111111111111",
  employee_id: "22222222-2222-2222-2222-222222222222",
  employee_name: "Jane Employee",
  leave_type_name: "Annual Leave",
  start_date: "2026-09-01",
  end_date: "2026-09-03",
  days_requested: 3,
  status: "PENDING",
};

function renderLeaveList() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LeaveList />
    </QueryClientProvider>
  );
}

describe("LeaveList reject dialog", () => {
  beforeEach(() => {
    getLeaveRequests.mockResolvedValue({ results: [PENDING_REQUEST] });
  });

  it("disables the reject button until a reason is entered", async () => {
    renderLeaveList();

    // Exact name — the status-filter tab's accessible name is "Rejected",
    // which a substring/regex match would also (wrongly) hit here.
    await userEvent.click(await screen.findByRole("button", { name: "Reject" }));

    const rejectRequestButton = await screen.findByRole("button", { name: /reject request/i });
    expect(rejectRequestButton).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/reason/i), "Insufficient staffing.");
    expect(rejectRequestButton).toBeEnabled();
  });
});
