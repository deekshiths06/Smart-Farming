import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Mail, Phone, UserRound } from "lucide-react";
import AuthLayout from "../components/AuthLayout";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { PasswordInput } from "../components/ui/PasswordInput";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { useAuth } from "../hooks/useAuth";
import { cn } from "../lib/cn";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 6;

function phoneIsValid(phone: string): boolean {
  const digits = phone.replace(/\D/g, "");
  return digits.length >= 7 && digits.length <= 15;
}

function describeRegisterError(error: unknown): string {
  const err = error as { response?: { data?: { detail?: unknown } } };
  if (!err?.response) {
    return "We couldn't reach the ANNADATA server. Check your connection and try again.";
  }
  const detail = err.response.data?.detail;
  if (typeof detail === "string") return detail;
  return "We couldn't create your account. Please try again in a moment.";
}

interface Errors {
  name?: string;
  email?: string;
  phone?: string;
  password?: string;
  confirm?: string;
}

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Errors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const passwordChecks = {
    length: password.length >= MIN_PASSWORD_LENGTH,
    letter: /[a-zA-Z]/.test(password),
    number: /\d/.test(password),
  };
  const passwordStrong =
    password.length > 0 && passwordChecks.length && passwordChecks.letter && passwordChecks.number;

  const clearError = (key: keyof Errors) =>
    setFieldErrors((current) => ({ ...current, [key]: undefined }));

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const next: Errors = {};
    if (!name.trim() || name.trim().length < 2) next.name = "Enter your full name.";
    if (!email.trim()) next.email = "Enter your email address.";
    else if (!EMAIL_PATTERN.test(email.trim())) next.email = "Enter a valid email address.";
    if (phone.trim() && !phoneIsValid(phone.trim())) {
      next.phone = "Enter a valid phone number.";
    }
    if (!password) next.password = "Choose a password.";
    else if (password.length < MIN_PASSWORD_LENGTH)
      next.password = `Passwords must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    if (confirm !== password) next.confirm = "Passwords don't match.";

    setFieldErrors(next);
    setSubmitError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        phone: phone.trim() || undefined,
      });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setSubmitError(describeRegisterError(error));
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Register as a farmer and start building a trusted record of your fields."
    >
      {submitError && (
        <ErrorAlert title="Couldn't create your account" message={submitError} className="mb-5" />
      )}
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Input
          id="register-name"
          label="Full name"
          type="text"
          autoComplete="name"
          placeholder="Priya Sharma"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            if (fieldErrors.name) clearError("name");
          }}
          error={fieldErrors.name}
          leadingIcon={<UserRound className="h-4 w-4" />}
        />
        <Input
          id="register-email"
          label="Email address"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            if (fieldErrors.email) clearError("email");
          }}
          error={fieldErrors.email}
          leadingIcon={<Mail className="h-4 w-4" />}
        />
        <Input
          id="register-phone"
          label="Phone number"
          type="tel"
          autoComplete="tel"
          placeholder="+91 98765 43210"
          value={phone}
          onChange={(event) => {
            setPhone(event.target.value);
            if (fieldErrors.phone) clearError("phone");
          }}
          error={fieldErrors.phone}
          hint="Optional — used if we ever need to reach you."
          leadingIcon={<Phone className="h-4 w-4" />}
        />
        <div>
          <PasswordInput
            id="register-password"
            label="Password"
            placeholder="At least 6 characters"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              if (fieldErrors.password) clearError("password");
            }}
            error={fieldErrors.password}
            hint={
              password.length > 0 ? (
                <ul className="mt-1.5 space-y-1">
                  {[
                    { check: passwordChecks.length, text: `At least ${MIN_PASSWORD_LENGTH} characters` },
                    { check: passwordChecks.letter, text: "Contains a letter" },
                    { check: passwordChecks.number, text: "Contains a number" },
                  ].map((item) => (
                    <li
                      key={item.text}
                      className={cn(
                        "flex items-center gap-1.5 text-[11px]",
                        item.check ? "text-brand-700" : "text-ink-muted"
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-3.5 w-3.5 items-center justify-center rounded-full text-[9px]",
                          item.check ? "bg-brand-600 text-white" : "bg-surface-sunken text-ink-muted"
                        )}
                      >
                        {item.check ? "✓" : ""}
                      </span>
                      {item.text}
                    </li>
                  ))}
                </ul>
              ) : undefined
            }
          />
          {passwordStrong && (
            <p className="mt-2 text-xs font-medium text-brand-700">
              Looks good — this password will work.
            </p>
          )}
        </div>
        <PasswordInput
          id="register-confirm"
          label="Confirm password"
          placeholder="Repeat your password"
          value={confirm}
          onChange={(event) => {
            setConfirm(event.target.value);
            if (fieldErrors.confirm) clearError("confirm");
          }}
          error={fieldErrors.confirm}
        />

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          rightIcon={<ArrowRight className="h-4 w-4" />}
        >
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-muted">
        Already have an account?{" "}
        <Link
          to="/login"
          className="font-semibold text-brand-700 transition-colors hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        >
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}