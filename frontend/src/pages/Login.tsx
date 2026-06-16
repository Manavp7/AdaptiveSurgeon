import { useState } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("surgeon");
  const [password, setPassword] = useState("surgeon123");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(username, password);
    } catch {
      setErr("Invalid credentials");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="panel login-card" onSubmit={submit}>
        <div className="brand" style={{ fontSize: 22 }}>
          AdaptiveSurgeon
          <small>Surgical Intelligence Operating System</small>
        </div>
        <div className="flex-col" style={{ marginTop: 18 }}>
          <label>
            <div className="small muted">Username</div>
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label>
            <div className="small muted">Password</div>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {err && <div className="err">{err}</div>}
          <button className="primary" disabled={busy} type="submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </div>
        <div className="demo-creds">
          <b>Demo accounts</b>
          <br />
          surgeon / surgeon123 &nbsp;(full workflow)
          <br />
          admin / admin123 &nbsp;(manage users)
          <br />
          viewer / viewer123 &nbsp;(read-only)
        </div>
      </form>
    </div>
  );
}
