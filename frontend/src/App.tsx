import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ProcedureDetail from "./pages/ProcedureDetail";
import NewCase from "./pages/NewCase";
import CaseSearch from "./pages/CaseSearch";
import About from "./pages/About";

function Sidebar() {
  const { username, role, logout } = useAuth();
  return (
    <aside className="sidebar">
      <div className="brand">
        AdaptiveSurgeon
        <small>Surgical Intelligence OS</small>
      </div>
      <nav className="flex-col" style={{ marginTop: 10 }}>
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          ▦ Dashboard
        </NavLink>
        <NavLink to="/new" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          ＋ New Surgery
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          ⌕ Case Search
        </NavLink>
        <NavLink to="/about" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          ⓘ Architecture
        </NavLink>
      </nav>
      <div className="spacer" />
      <div className="user-box">
        <div>
          {username}
          <span className="role-pill">{role}</span>
        </div>
        <button style={{ marginTop: 10, width: "100%" }} onClick={logout}>
          Sign out
        </button>
      </div>
    </aside>
  );
}

export default function App() {
  const { username, ready } = useAuth();
  if (!ready) return <div className="spinner">Loading…</div>;
  if (!username) return <Login />;

  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <div className="disclaimer">
          ⚠ Research prototype — <b>ADVISORY ONLY</b>, not a medical device. All data is synthetic.
        </div>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/procedures/:id" element={<ProcedureDetail />} />
          <Route path="/new" element={<NewCase />} />
          <Route path="/search" element={<CaseSearch />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
