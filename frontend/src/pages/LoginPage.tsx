import { Loader2, Music2, UserRound, WifiOff } from "lucide-react";
import type { FormEvent } from "react";
import type { AuthProviders } from "../types";
import { CornerWaveBg } from "../components/WaveformEffects";
import { AppleIcon, GoogleIcon } from "../components/Icons";

export interface LoginPageProps {
  email: string;
  onEmailChange: (email: string) => void;
  password: string;
  onPasswordChange: (pass: string) => void;
  authError: string;
  authBusy: boolean;
  authProviders: AuthProviders;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  onStartOAuth: (provider: "google" | "apple") => void;
  onNavigateToRegister: () => void;
  online: boolean;
}

export function LoginPage({
  email,
  onEmailChange,
  password,
  onPasswordChange,
  authError,
  authBusy,
  authProviders,
  onSubmit,
  onStartOAuth,
  onNavigateToRegister,
  online
}: LoginPageProps) {
  return (
    <main className="auth-page login-page">
      <section className="auth-panel">
        <CornerWaveBg />
        <div>
          <div className="brand-lockup">
            <Music2 size={26} />
            <span>StemSplit AI</span>
          </div>
          <h1>Sign in to your workspace</h1>
        </div>
        <form onSubmit={onSubmit} className="auth-form">
          <label>
            <span>Email</span>
            <input
              autoComplete="email"
              value={email}
              onChange={(event) => onEmailChange(event.target.value)}
              type="email"
              required
            />
          </label>
          <label>
            <span>Password</span>
            <input
              autoComplete="current-password"
              value={password}
              onChange={(event) => onPasswordChange(event.target.value)}
              type="password"
              minLength={8}
              required
            />
          </label>
          {authError && <p className="error-line">{authError}</p>}
          <button className="primary-btn" disabled={authBusy} type="submit">
            {authBusy ? <Loader2 className="spin" size={17} /> : <UserRound size={17} />}
            Sign in
          </button>
        </form>

        <div className="social-auth-block">
          <div className="auth-divider">
            <span>or continue with</span>
          </div>
          <div className="provider-grid">
            <button
              className="provider-btn"
              disabled={!authProviders.google || authBusy}
              onClick={() => onStartOAuth("google")}
              title={
                authProviders.google
                  ? "Continue with Google"
                  : "Google OAuth is not configured"
              }
              type="button"
            >
              <span className="provider-mark google-mark">
                <GoogleIcon />
              </span>
              Continue with Google
            </button>
            <button
              className="provider-btn"
              disabled={!authProviders.apple || authBusy}
              onClick={() => onStartOAuth("apple")}
              title={
                authProviders.apple ? "Continue with Apple" : "Apple OAuth is not configured"
              }
              type="button"
            >
              <span className="provider-mark apple-mark">
                <AppleIcon />
              </span>
              Continue with Apple
            </button>
          </div>
        </div>

        <button
          className="text-btn"
          onClick={onNavigateToRegister}
          type="button"
        >
          Create a new workspace
        </button>

        {!online && (
          <div className="offline-note">
            <WifiOff size={16} />
            API access requires a network connection.
          </div>
        )}
      </section>
    </main>
  );
}
