import { useEffect, useState } from "react";
import { api } from "../api";
import { FONT_MONO, SOURCE, T } from "../theme";
import type { SoundcloudStatus } from "../types";

const SC = SOURCE.soundcloud;

export default function SoundCloudConnect() {
  const [status, setStatus] = useState<SoundcloudStatus | null>(null);
  const [editing, setEditing] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSoundcloudStatus().then(setStatus).catch(() => {});
  }, []);

  async function connect() {
    if (!token.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const s = await api.connectSoundcloud(token.trim());
      setStatus(s);
      setEditing(false);
      setToken("");
    } catch (e) {
      setError(String(e).replace(/^Error:\s*\d+:\s*/, "").replace(/^\{.*"detail":"?|"?\}$/g, ""));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    try {
      setStatus(await api.disconnectSoundcloud());
    } finally {
      setBusy(false);
    }
  }

  if (!status) return null;
  const connected = status.connected;

  return (
    <div
      style={{
        marginTop: 14,
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
            color: SC.color,
            background: SC.bg,
            borderRadius: 999,
            padding: "4px 9px",
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: SC.color }} />
          SoundCloud
        </span>

        {connected ? (
          <>
            <span style={{ fontSize: 13, color: T.text2 }}>
              Connected
              {status.username && (
                <>
                  {" as "}
                  <span style={{ fontWeight: 600, color: T.text }}>{status.username}</span>
                </>
              )}
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
              Connect your account to download auth-gated / original-quality tracks.
            </span>
            {!editing && (
              <button type="button" onClick={() => setEditing(true)} style={primaryBtn}>
                Connect
              </button>
            )}
          </>
        )}
      </div>

      {!connected && editing && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", gap: 9, flexWrap: "wrap" }}>
            <input
              className="dc-input"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="oauth_token (e.g. 2-1234567-...)"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && connect()}
              style={{
                flex: 1,
                minWidth: 220,
                background: T.inset,
                border: `1px solid ${T.borderStrong}`,
                borderRadius: 9,
                color: T.text,
                padding: "10px 13px",
                fontFamily: FONT_MONO,
                fontSize: 13,
                outline: "none",
              }}
            />
            <button type="button" onClick={connect} disabled={!token.trim() || busy} style={primaryBtn}>
              {busy ? "Verifying…" : "Verify & save"}
            </button>
            <button
              type="button"
              onClick={() => {
                setEditing(false);
                setError(null);
                setToken("");
              }}
              style={ghostBtn}
            >
              Cancel
            </button>
          </div>

          {error && (
            <p
              style={{
                margin: "9px 0 0",
                fontSize: 12,
                color: "#e3a3ac",
              }}
            >
              {error}
            </p>
          )}

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
            {showHelp ? "▾" : "▸"} How do I get my oauth_token?
          </button>
          {showHelp && (
            <ol
              style={{
                margin: "8px 0 0",
                paddingLeft: 18,
                fontSize: 12,
                lineHeight: 1.7,
                color: T.muted,
              }}
            >
              <li>
                Log into <span style={{ color: T.text2 }}>soundcloud.com</span> in your browser.
              </li>
              <li>
                Open DevTools (F12) →{" "}
                <span style={{ color: T.text2 }}>Application</span> →{" "}
                <span style={{ color: T.text2 }}>Cookies</span> → https://soundcloud.com.
              </li>
              <li>
                Copy the full value of the{" "}
                <span style={{ fontFamily: FONT_MONO, color: T.text2 }}>oauth_token</span> cookie and
                paste it above.
              </li>
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

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
