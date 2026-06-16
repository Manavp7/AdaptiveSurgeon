import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth";

interface U {
  id: string;
  username: string;
  full_name: string;
  role: string;
}

export default function AdminUsers() {
  const { role } = useAuth();
  const [users, setUsers] = useState<U[]>([]);
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState("viewer");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.listUsers().then(setUsers).catch((e) => setErr(String(e)));
  useEffect(() => {
    if (role === "admin") load();
  }, [role]);

  if (role !== "admin") {
    return (
      <div>
        <h1 className="page-title">User Management</h1>
        <div className="panel">Admin access required.</div>
      </div>
    );
  }

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api.createUser({ username, password, full_name: fullName, role: newRole });
      setUsername("");
      setFullName("");
      setPassword("");
      await load();
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">User Management</h1>
      <p className="page-sub">Minimal RBAC — create accounts and assign roles.</p>

      <div className="grid" style={{ gridTemplateColumns: "1.4fr 1fr" }}>
        <div className="panel">
          <h3>Users</h3>
          <table>
            <thead><tr><th>Username</th><th>Name</th><th>Role</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td className="muted">{u.full_name || "—"}</td>
                  <td><span className="role-pill">{u.role}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h3>Add user</h3>
          <form className="flex-col" onSubmit={create}>
            <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <input placeholder="full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            <input placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
              <option value="viewer">viewer</option>
              <option value="surgeon">surgeon</option>
              <option value="admin">admin</option>
            </select>
            {err && <div className="err">{err}</div>}
            <button className="primary" disabled={busy} type="submit">{busy ? "Creating…" : "Create user"}</button>
          </form>
        </div>
      </div>
    </div>
  );
}
