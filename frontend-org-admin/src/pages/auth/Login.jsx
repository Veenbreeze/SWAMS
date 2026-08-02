import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [organizationCode, setOrganizationCode] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ organizationCode, identifier, password });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to sign in. Check your credentials and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in to SWAMS</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="organizationCode">Organization code</Label>
            <Input
              id="organizationCode"
              placeholder="ABC001"
              value={organizationCode}
              onChange={(e) => setOrganizationCode(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="identifier">Email or employee ID</Label>
            <Input
              id="identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
