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
  it("requires organization code, identifier, and password before submitting", async () => {
    const login = vi.fn();
    renderLogin(login);

    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(login).not.toHaveBeenCalled();
  });

  it("submits the entered credentials", async () => {
    const login = vi.fn().mockResolvedValue({});
    renderLogin(login);

    await userEvent.type(screen.getByLabelText(/organization code/i), "ABC001");
    await userEvent.type(screen.getByLabelText(/email or employee id/i), "admin@example.com");
    await userEvent.type(screen.getByLabelText(/^password$/i), "Sup3rSecret!Pass");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith({
        organizationCode: "ABC001",
        identifier: "admin@example.com",
        password: "Sup3rSecret!Pass",
      })
    );
  });

  it("shows the backend error message when login fails", async () => {
    const login = vi.fn().mockRejectedValue({ message: "Invalid organization code, identifier, or password." });
    renderLogin(login);

    await userEvent.type(screen.getByLabelText(/organization code/i), "ABC001");
    await userEvent.type(screen.getByLabelText(/email or employee id/i), "admin@example.com");
    await userEvent.type(screen.getByLabelText(/^password$/i), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText("Invalid organization code, identifier, or password.")
    ).toBeInTheDocument();
  });
});
