import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Mail, ArrowRight } from "lucide-react";
import AuthLayout from "../components/AuthLayout";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { PasswordInput } from "../components/ui/PasswordInput";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { useAuth } from "../hooks/useAuth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function describeLoginError(error: unknown): string {
  const err = error as { response?: { status?: number; data?: { detail?: unknown } } };
  if (!err?.response) {
    return "We couldn't reach the ANNADATA server. Check your connection and try again.";
  }
  const detail = err.response.data?.detail;
  if (
    err.response.status === 400 &&
    (detail === "Incorrect email or password" || typeof detail === "string")
  ) {
    return "That email or password doesn't match our records. Please try again.";
  }
  return "Logging in didn't work. Please try again in a moment.";
}

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = useMemo(() => {
    const state = location.state as { from?: string } | null;
    return state?.from && state.from !== "/login" ? state.from : "/dashboard";
  }, [location.state]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const next: { email?: string; password?: string } = {};
    if (!email.trim()) next.email = "Enter your email address.";
    else if (!EMAIL_PATTERN.test(email.trim())) next.email = "Enter a valid email address.";
    if (!password) next.password = "Enter your password.";

    setFieldErrors(next);
    setSubmitError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (error) {
      setSubmitError(describeLoginError(error));
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to your ANNADATA workspace and pick up where you left off."
    >
      {submitError && (
        <ErrorAlert title="Unable to log in" message={submitError} className="mb-5" />
      )}
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Input
          id="login-email"
          label="Email address"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            if (fieldErrors.email) setFieldErrors((current) => ({ ...current, email: undefined }));
          }}
          error={fieldErrors.email}
          leadingIcon={<Mail className="h-4 w-4" />}
        />
        <div>
          <PasswordInput
            id="login-password"
            label="Password"
            placeholder="Your password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              if (fieldErrors.password)
                setFieldErrors((current) => ({ ...current, password: undefined }));
            }}
            error={fieldErrors.password}
          />
        </div>

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          rightIcon={<ArrowRight className="h-4 w-4" />}
        >
          Log in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-muted">
        New to ANNADATA?{" "}
        <Link
          to="/register"
          className="font-semibold text-brand-700 transition-colors hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        >
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}