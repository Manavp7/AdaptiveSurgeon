import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api/client";
import type { Role } from "./types";

interface AuthState {
  username: string | null;
  role: Role | null;
  ready: boolean;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState>(null as unknown as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      if (getToken()) {
        try {
          const me = await api.me();
          setUsername(me.username);
          setRole(me.role as Role);
        } catch {
          setToken(null);
        }
      }
      setReady(true);
    })();
  }, []);

  const login = async (u: string, p: string) => {
    const res = await api.login(u, p);
    setToken(res.access_token);
    setUsername(res.username);
    setRole(res.role as Role);
  };

  const logout = () => {
    setToken(null);
    setUsername(null);
    setRole(null);
  };

  return (
    <AuthCtx.Provider value={{ username, role, ready, login, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);

export function canWrite(role: Role | null): boolean {
  return role === "surgeon" || role === "admin";
}
