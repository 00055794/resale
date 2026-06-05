import { useState } from "react";

export type Session = {
  name: string;
  iinRegion: string;
  income: number;
};

type Props = {
  session: Session | null;
  onLogin: (s: Session) => void;
  onLogout: () => void;
};

/**
 * Halyk SSO login bar. In demo mode the OIDC exchange is mocked and returns a fixed
 * client profile, mirroring the server MockHalykSSOAdapter. Production swaps this for a
 * real authorization-code redirect to the Halyk identity provider.
 */
export default function LoginBar({ session, onLogin, onLogout }: Props) {
  const [busy, setBusy] = useState(false);

  const login = () => {
    setBusy(true);
    // Mocked OIDC exchange: matches server MockHalykSSOAdapter profile.
    window.setTimeout(() => {
      onLogin({ name: "Демо Клиент", iinRegion: "Алматы", income: 850000 });
      setBusy(false);
    }, 300);
  };

  if (session) {
    return (
      <div className="loginbar">
        <span className="muted">
          {session.name} · регион по ИИН: {session.iinRegion}
        </span>
        <button className="btn ghost small" onClick={onLogout}>
          Выйти
        </button>
      </div>
    );
  }

  return (
    <div className="loginbar">
      <span className="muted">Войдите через Halyk SSO для персонализации</span>
      <button className="btn primary small" onClick={login} disabled={busy}>
        {busy ? "Вход..." : "Войти через Halyk SSO"}
      </button>
    </div>
  );
}
