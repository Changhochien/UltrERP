/** Login page – email + password form. */

import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { HOME_ROUTE } from "../lib/routes";

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={HOME_ROUTE} replace />;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const result = await login(email, password);
    setSubmitting(false);
    if (result.ok) {
      navigate(HOME_ROUTE, { replace: true });
    } else {
      setError(result.error ?? "Login failed");
    }
  }

  return (
    <main className="app-shell" style={{ maxWidth: "400px", margin: "4rem auto" }}>
      <h1>UltrERP Login</h1>
      <form onSubmit={handleSubmit}>
        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        <div className="form-field">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
          />
        </div>
        <div className="form-field">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Logging in…" : "Log in"}
        </button>
      </form>
    </main>
  );
}
