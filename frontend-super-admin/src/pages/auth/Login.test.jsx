import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext } from "@/context/AuthContext";
import Login from "@/pages/auth/Login";

function renderLogin(login) {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={{ login }}>
        <Login />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("Login", () => {
  it("requires email and password before submitting", async () => {
    const login = vi.fn();
    renderLogin(login);

    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(login).not.toHaveBeenCalled();
  });

  it("submits the entered credentials without an organization code field", async () => {
    const login = vi.fn().mockResolvedValue({});
    renderLogin(login);

    expect(screen.queryByLabelText(/organization code/i)).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/email/i), "super@demo.test");
    await userEvent.type(screen.getByLabelText(/password/i), "Sup3rSecret!Pass");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith({
        identifier: "super@demo.test",
        password: "Sup3rSecret!Pass",
      })
    );
  });

  it("shows the backend error message when login fails", async () => {
    const login = vi.fn().mockRejectedValue({ message: "Invalid credentials." });
    renderLogin(login);

    await userEvent.type(screen.getByLabelText(/email/i), "super@demo.test");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Invalid credentials.")).toBeInTheDocument();
  });
});
