import { useEffect, useState } from "react";
import { api } from "../api";
import { FONT_MONO, SOURCE, T } from "../theme";
import type { SpotifyStatus } from "../types";

const SP = SOURCE.spotify;

export default function SpotifyConnect({
  onChange,
}: {
  onChange?: (configured: boolean) => void;
}) {
  const [status, setStatus] = useState<SpotifyStatus | null>(null);
  const [editing, setEditing] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSpotifyStatus().then(setStatus).catch(() => {});
  }, []);

  function apply(s: SpotifyStatus) {
    setStatus(s);
    onChange?.(s.configured);
  }

  async function connect() {
    if (!clientId.trim() || !clientSecret.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      apply(await api.connectSpotify(clientId.trim(), clientSecret.trim()));
      setEditing(false);
      setClientId("");
      setClientSecret("");
    } catch (e) {
      setError(String(e).replace(/^Error:\s*\d+:\s*/, "").replace(/^\{.*"detail":"?|"?\}$/g, ""));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    try {
      apply(await api.disconnectSpotify());
    } finally {
      setBusy(false);
    }
  }

  if (!status) return null;

  return (
    <div
      style={{
        marginTop: 10,
        background: T.panel,
        border: `1px solid ${T.border}`,
        borderRadius: 12,
        padding: "13px 15px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 11, flexWrap: "wrap" }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontFamily: FONT_MONO,
            fontSize: 11,
            fontWeight: 500,
            color: SP.color,
            background: SP.bg,
            borderRadius: 999,
            padding: "4px 9px",
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: SP.color }} />
          Spotify
        </span>

        {status.configured ? (
          <>
            <span style={{ fontSize: 13, color: T.text2 }}>
              API credentials connected
              {status.source === "env" && (
                <span style={{ color: T.faint2, fontSize: 12 }}> (from .env)</span>
              )}
            </span>
            <span style={{ flex: 1 }} />
            {status.source === "app" && (
              <button type="button" onClick={disconnect} disabled={busy} style={ghostBtn}>
                Disconnect
              </button>
            )}
          </>
        ) : (
          <>
            <span style={{ fontSize: 13, color: T.muted, flex: 1, minWidth: 180 }}>
              Add your Spotify API credentials for reliable metadata &amp; covers.
            </span>
            {!editing && (
              <button type="button" onClick={() => setEditing(true)} style={primaryBtn}>
                Connect
              </button>
            )}
          </>
        )}
      </div>

      {!status.configured && editing && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", gap: 9, flexWrap: "wrap" }}>
            <input
              className="dc-input"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="Client ID"
              autoFocus
              style={inputStyle}
            />
            <input
              className="dc-input"
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="Client Secret"
              onKeyDown={(e) => e.key === "Enter" && connect()}
              style={inputStyle}
            />
          </div>
          <div style={{ display: "flex", gap: 9, marginTop: 9, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={connect}
              disabled={!clientId.trim() || !clientSecret.trim() || busy}
              style={primaryBtn}
            >
              {busy ? "Verifying…" : "Verify & save"}
            </button>
            <button
              type="button"
              onClick={() => {
                setEditing(false);
                setError(null);
                setClientId("");
                setClientSecret("");
              }}
              style={ghostBtn}
            >
              Cancel
            </button>
          </div>

          {error && <p style={{ margin: "9px 0 0", fontSize: 12, color: "#e3a3ac" }}>{error}</p>}

          <button
            type="button"
            onClick={() => setShowHelp((v) => !v)}
            style={{
              marginTop: 9,
              background: "none",
              border: "none",
              padding: 0,
              cursor: "pointer",
              fontFamily: FONT_MONO,
              fontSize: 11,
              color: T.accent,
            }}
          >
            {showHelp ? "▾" : "▸"} How do I get Spotify API credentials?
          </button>
          {showHelp && (
            <ol
              style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 12, lineHeight: 1.7, color: T.muted }}
            >
              <li>
                Go to{" "}
                <span style={{ color: T.text2 }}>developer.spotify.com/dashboard</span> and log in.
              </li>
              <li>
                <span style={{ color: T.text2 }}>Create app</span> — any name/description; redirect
                URI can be <span style={{ fontFamily: FONT_MONO }}>http://localhost</span>.
              </li>
              <li>
                Open the app's <span style={{ color: T.text2 }}>Settings</span> and copy the{" "}
                <span style={{ color: T.text2 }}>Client ID</span> and{" "}
                <span style={{ color: T.text2 }}>Client Secret</span> here.
              </li>
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 200,
  background: T.inset,
  border: `1px solid ${T.borderStrong}`,
  borderRadius: 9,
  color: T.text,
  padding: "10px 13px",
  fontFamily: FONT_MONO,
  fontSize: 13,
  outline: "none",
};

const primaryBtn: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 7,
  height: 38,
  padding: "0 16px",
  border: "none",
  borderRadius: 9,
  background: T.accent,
  color: T.onAccent,
  fontWeight: 600,
  fontSize: 13,
  cursor: "pointer",
  boxShadow: "0 8px 24px -8px color-mix(in srgb, #00e0c6 70%, transparent)",
};

const ghostBtn: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  height: 38,
  padding: "0 14px",
  border: `1px solid ${T.borderStrong}`,
  borderRadius: 9,
  background: "rgba(255,255,255,0.04)",
  color: T.text2,
  fontSize: 13,
  cursor: "pointer",
};
