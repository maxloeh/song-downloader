import { useState } from "react";
import { api } from "../api";
import { FONT_MONO, T } from "../theme";

interface Props {
  mode: "login" | "setup";
  onAuthed: () => void;
}

export default function AuthScreen({ mode, onAuthed }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSetup = mode === "setup";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    if (isSetup && password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setBusy(true);
    try {
      if (isSetup) await api.setup(username.trim(), password);
      else await api.login(username.trim(), password);
      onAuthed();
    } catch (e2) {
      setError(String(e2).replace(/^Error:\s*\d+:\s*/, "").replace(/^\{.*"detail":"?|"?\}$/g, ""));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        position: "relative",
        zIndex: 1,
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 16px",
      }}
    >
      <div style={{ width: "100%", maxWidth: 380 }}>
        {/* Animated waveform */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            gap: 3,
            height: 42,
            marginBottom: 26,
          }}
        >
          {Array.from({ length: 13 }).map((_, i) => (
            <i
              key={i}
              style={{
                width: 4,
                height: "100%",
                borderRadius: 2,
                background: T.accent,
                transformOrigin: "bottom",
                animation: `wave ${0.9 + (i % 5) * 0.12}s ease-in-out ${i * 0.07}s infinite`,
                opacity: 0.85,
              }}
            />
          ))}
        </div>

        <div style={{ textAlign: "center", marginBottom: 26 }}>
          <h1 style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em" }}>
            music<span style={{ color: T.accent }}>-dl</span>
          </h1>
          <p style={{ margin: "8px 0 0", fontSize: 13, color: T.muted, lineHeight: 1.5 }}>
            {isSetup
              ? "Welcome! Create your account to get started."
              : "Private SoundCloud & Spotify downloader. Sign in to continue."}
          </p>
        </div>

        <form
          onSubmit={submit}
          style={{
            background: T.panel,
            border: `1px solid ${T.border}`,
            borderRadius: 14,
            padding: 22,
            boxShadow: "0 24px 60px -28px rgba(0,0,0,0.8)",
          }}
        >
          <Field label="Username">
            <input
              className="dc-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              style={inputStyle}
            />
          </Field>
          <Field label="Password">
            <input
              className="dc-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isSetup ? "new-password" : "current-password"}
              style={inputStyle}
            />
          </Field>
          {isSetup && (
            <Field label="Confirm password">
              <input
                className="dc-input"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                style={inputStyle}
              />
            </Field>
          )}

          {error && (
            <p style={{ margin: "0 0 14px", fontSize: 12.5, color: "#e3a3ac" }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={busy || !username.trim() || !password}
            style={{
              width: "100%",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              height: 46,
              border: "none",
              borderRadius: 9,
              background: T.accent,
              color: T.onAccent,
              fontWeight: 600,
              fontSize: 14,
              cursor: busy ? "default" : "pointer",
              opacity: busy || !username.trim() || !password ? 0.55 : 1,
              boxShadow: "0 8px 28px -8px color-mix(in srgb, #00e0c6 75%, transparent)",
            }}
          >
            {busy ? "…" : isSetup ? "Create account →" : "Sign in →"}
          </button>
        </form>

        <p
          style={{
            textAlign: "center",
            margin: "18px 0 0",
            fontFamily: FONT_MONO,
            fontSize: 10,
            color: T.faint4,
            letterSpacing: "0.04em",
          }}
        >
          private instance · keep it on your own network / Tailscale
        </p>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block", marginBottom: 16 }}>
      <span
        style={{
          display: "block",
          fontFamily: FONT_MONO,
          fontSize: 10,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: T.faint,
          marginBottom: 7,
        }}
      >
        {label}
      </span>
      {children}
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: T.inset,
  border: `1px solid ${T.borderStrong}`,
  borderRadius: 9,
  color: T.text,
  padding: "12px 14px",
  fontSize: 14,
  outline: "none",
};
