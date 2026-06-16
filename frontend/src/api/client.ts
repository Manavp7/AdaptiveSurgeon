import type {
  AskResponse,
  DigitalTwinT,
  Page,
  Patient,
  Procedure,
  ProcedureDetail,
  SimilarCase,
  UnifiedAnalysis,
  VitalsResponse,
} from "../types";

const TOKEN_KEY = "adaptive_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function tryRefresh(): Promise<boolean> {
  const token = getToken();
  if (!token) return false;
  try {
    const res = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return false;
    const j = (await res.json()) as { access_token: string };
    setToken(j.access_token);
    return true;
  } catch {
    return false;
  }
}

async function req<T>(path: string, opts: RequestInit = {}, _retried = false): Promise<T> {
  const headers = new Headers(opts.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (opts.body && !(opts.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`/api${path}`, { ...opts, headers });
  if (!res.ok) {
    // One automatic refresh+retry on 401 (skip the refresh endpoint itself).
    if (res.status === 401 && !_retried && !path.startsWith("/auth/")) {
      if (await tryRefresh()) return req<T>(path, opts, true);
    }
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const api = {
  // auth
  async login(username: string, password: string) {
    const body = new URLSearchParams({ username, password });
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new ApiError(res.status, "Invalid credentials");
    return res.json() as Promise<{ access_token: string; role: string; username: string }>;
  },
  me: () => req<{ id: string; username: string; full_name: string; role: string }>("/auth/me"),

  // data platform
  listProcedures: (limit = 200, offset = 0) =>
    req<Page<Procedure>>(`/procedures?limit=${limit}&offset=${offset}`),
  getProcedure: (id: string) => req<ProcedureDetail>(`/procedures/${id}`),
  listPatients: (limit = 500, offset = 0) =>
    req<Page<Patient>>(`/patients?limit=${limit}&offset=${offset}`),
  createPatient: (body: Partial<Patient>) =>
    req<Patient>("/patients", { method: "POST", body: JSON.stringify(body) }),
  createProcedure: (body: { patient_id: string; procedure_type: string; surgeon_name?: string }) =>
    req<Procedure>("/procedures", { method: "POST", body: JSON.stringify(body) }),
  uploadMedia: (procedureId: string, file: File, kind = "video") => {
    const fd = new FormData();
    fd.append("procedure_id", procedureId);
    fd.append("kind", kind);
    fd.append("file", file);
    return req<{ id: string }>("/media", { method: "POST", body: fd });
  },

  // analysis
  analyze: (id: string) =>
    req<{ job_id: string; status: string }>(`/procedures/${id}/analyze`, { method: "POST" }),
  getJob: (jobId: string) =>
    req<{ id: string; status: string; progress: number; message: string; error: string | null }>(
      `/jobs/${jobId}`
    ),
  /** Run analysis and resolve when the background job finishes (polls progress). */
  async analyzeAndWait(id: string, onProgress?: (p: number, msg: string) => void) {
    const { job_id } = await this.analyze(id);
    for (;;) {
      const job = await this.getJob(job_id);
      onProgress?.(job.progress, job.message);
      if (job.status === "done") return job;
      if (job.status === "error") throw new ApiError(500, job.error || "Analysis failed");
      await new Promise((r) => setTimeout(r, 600));
    }
  },
  getAnalysis: (id: string) => req<UnifiedAnalysis>(`/procedures/${id}/analysis`),
  getVitals: (id: string) => req<VitalsResponse>(`/procedures/${id}/vitals`),
  getTwin: (id: string) => req<DigitalTwinT>(`/procedures/${id}/twin`),

  // foundation
  similar: (id: string, topK = 6) =>
    req<{ results: SimilarCase[]; provider: string }>(`/foundation/similar?procedure_id=${id}&top_k=${topK}`),
  search: (q: string, topK = 8) =>
    req<{ results: SimilarCase[]; provider: string }>(`/foundation/search?q=${encodeURIComponent(q)}&top_k=${topK}`),
  ask: (question: string, procedureId?: string) =>
    req<AskResponse>("/foundation/ask", {
      method: "POST",
      body: JSON.stringify({ question, procedure_id: procedureId ?? null }),
    }),
};
