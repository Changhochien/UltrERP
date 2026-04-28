/** Login page – email + password form. */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router-dom";

import { ThemeToggle } from "../components/theme/ThemeToggle";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { useAuth } from "../hooks/useAuth";
import { HOME_ROUTE } from "../lib/routes";

export default function LoginPage() {
  const { t } = useTranslation("auth");
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
      setError(result.error ?? t("auth.error"));
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center px-6 py-16">
      <div className="grid w-full gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(22rem,28rem)] lg:items-center">
        <section className="space-y-6">
          <div className="inline-flex items-center rounded-full border border-border/80 bg-background/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-primary/80">
            UltrERP
          </div>
          <div className="space-y-3">
            <h1 className="max-w-xl text-4xl font-semibold tracking-tight sm:text-5xl">{t("auth.title")}</h1>
            <p className="max-w-xl text-base leading-7 text-muted-foreground">
              {t("auth.subtitle")}
            </p>
          </div>
        </section>

        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle>{t("auth.welcome")}</CardTitle>
              <CardDescription>{t("auth.shellDescription")}</CardDescription>
            </div>
            <ThemeToggle />
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error ? (
                <p className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive" role="alert">
                  {error}
                </p>
              ) : null}
              <div className="space-y-2">
                <label htmlFor="login-email">{t("auth.email")}</label>
                <Input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="login-password">{t("auth.password")}</label>
                <Input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? t("auth.loggingIn") : t("auth.login")}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
