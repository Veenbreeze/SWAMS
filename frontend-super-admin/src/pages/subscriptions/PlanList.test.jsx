import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlanList from "@/pages/subscriptions/PlanList";

vi.mock("@/api/endpoints/subscriptions", () => ({
  getPlans: vi.fn(),
  createPlan: vi.fn(),
  updatePlan: vi.fn(),
  getSubscriptions: vi.fn(),
  assignSubscription: vi.fn(),
  cancelSubscription: vi.fn(),
  getExpiryMonitor: vi.fn(),
}));
vi.mock("@/api/endpoints/organizations", () => ({
  getOrganizations: vi.fn(),
}));

import { getOrganizations } from "@/api/endpoints/organizations";
import { getPlans, getSubscriptions } from "@/api/endpoints/subscriptions";

const PLAN = {
  id: "plan-1",
  code: "BASIC",
  name: "Basic",
  monthly_price: "50.00",
  max_employees: 25,
  max_branches: 2,
  grace_period_days: 7,
  is_active: true,
};

const ORG = { id: "org-1", code: "DEMO001", name: "Demo Org" };

function renderPlanList() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PlanList />
    </QueryClientProvider>
  );
}

describe("PlanList assign-subscription dialog", () => {
  beforeEach(() => {
    getPlans.mockResolvedValue({ results: [PLAN] });
    getSubscriptions.mockResolvedValue({ results: [] });
    getOrganizations.mockResolvedValue({ results: [ORG] });
  });

  it("disables Assign until organization, plan, and both dates are set", async () => {
    renderPlanList();

    await userEvent.click(await screen.findByRole("button", { name: /assign subscription/i }));

    const assignButton = await screen.findByRole("button", { name: /^assign$/i });
    expect(assignButton).toBeDisabled();

    await userEvent.selectOptions(screen.getByLabelText(/organization/i), ORG.id);
    await userEvent.selectOptions(screen.getByLabelText(/^plan$/i), PLAN.id);
    expect(assignButton).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/start date/i), "2026-08-03");
    await userEvent.type(screen.getByLabelText(/expiry date/i), "2027-08-03");

    expect(assignButton).toBeEnabled();
  });
});
