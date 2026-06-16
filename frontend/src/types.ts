export type Role = "admin" | "surgeon" | "viewer";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Patient {
  id: string;
  external_mrn: string;
  display_name: string;
  age: number | null;
  sex: string | null;
  bmi: number | null;
  history: Record<string, unknown>;
  created_at: string;
}

export interface Procedure {
  id: string;
  patient_id: string;
  procedure_type: string;
  surgeon_id: string;
  surgeon_name: string;
  started_at: string | null;
  ended_at: string | null;
  status: string;
  notes: string;
  created_at: string;
}

export interface Media {
  id: string;
  procedure_id: string;
  kind: string;
  uri: string;
  filename: string;
  content_type: string;
  duration_s: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  meta: Record<string, unknown>;
}

export interface OutcomeT {
  id: string;
  procedure_id: string;
  discharge_summary: string;
  complications: unknown[];
  length_of_stay_days: number | null;
  readmission_30d: boolean;
  mortality: boolean;
  notes: string;
}

export interface ProcedureDetail extends Procedure {
  patient: Patient;
  media: Media[];
  events: EventT[];
  outcome: OutcomeT | null;
}

export interface EventT {
  id: string;
  procedure_id: string;
  kind: string;
  label: string;
  t_start_s: number;
  t_end_s: number | null;
  severity: string;
  payload: Record<string, unknown>;
}

export interface Detection {
  frame_idx: number;
  t_s: number;
  class_name: string;
  confidence: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Track {
  track_id: number;
  class_name: string;
  path_length_m: number;
  mean_speed_cm_s: number;
  max_speed_cm_s: number;
  idle_time_s: number;
  active_time_s: number;
  jerk: number;
  points: number[][];
}

export interface AnatomyMask {
  t_s: number;
  class_name: string;
  criticality: "safe" | "caution" | "critical";
  confidence: number;
  polygon: number[][];
}

export interface PhaseSegment {
  phase: string;
  order_idx: number;
  t_start_s: number;
  t_end_s: number;
  confidence: number;
}

export interface SkillReport {
  score: number;
  surgeon_id: string;
  subscores: Record<string, number>;
  findings: string[];
}

export interface RiskAssessment {
  t_s: number;
  event_type: string;
  probability: number;
  severity: string;
  drivers: string[];
}

export interface Advisory {
  t_start_s: number;
  t_end_s: number | null;
  label: string;
  severity: string;
  payload: Record<string, unknown>;
}

export interface UnifiedAnalysis {
  procedure_id: string;
  status: string;
  video_uri: string | null;
  video_duration_s: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  phases: PhaseSegment[];
  anatomy: AnatomyMask[];
  tracks: Track[];
  detection_count: number;
  detections_sample: Detection[];
  skill: SkillReport | null;
  risks: RiskAssessment[];
  advisories: Advisory[];
}

export interface TwinStructure {
  name: string;
  criticality: "safe" | "caution" | "critical";
  color: string;
  geometry: Record<string, unknown>;
}

export interface PlanClearance {
  structure: string;
  criticality: string;
  clearance: number;
  breach: boolean;
}

export interface PlanResult {
  entry: number[];
  target: number[];
  trajectory: number[][];
  clearances: PlanClearance[];
  min_critical_clearance: number;
  safety_score: number;
  safe: boolean;
  warnings: string[];
  disclaimer: string;
}

export interface DigitalTwinT {
  id: string;
  procedure_id: string;
  source_modality: string;
  structures: TwinStructure[];
  mesh_uri: string | null;
  expected_vs_actual: Array<Record<string, unknown>>;
}

export interface SimilarCase {
  procedure_id: string;
  procedure_type: string;
  similarity: number;
  text_summary: string;
  complications: unknown[];
  outcome_summary: string;
}

export interface ImagingStudy {
  id: string;
  kind: string;
  modality: string;
  depth: number;
  rows: number | null;
  cols: number | null;
  description: string;
  filename: string;
}

export interface DicomVolume {
  modality: string;
  depth: number;
  rows: number;
  cols: number;
  pixel_spacing: [number, number] | number[];
  slice_thickness: number;
  is_hu: boolean;
  value_min: number;
  value_max: number;
  default_window: [number, number] | number[];
  window_presets: Record<string, (number | null)[]>;
  dtype: string;
  data_b64: string;
}

export interface VitalPoint {
  t: number;
  hr: number;
  bp_sys: number;
  bp_dia: number;
  spo2: number;
}

export interface VitalsResponse {
  procedure_id: string;
  source: string | null;
  series: VitalPoint[];
}

export interface SurgeonScorecard {
  surgeon: string;
  cases: number;
  analyzed: number;
  avg_skill: number | null;
  complication_rate: number;
  procedure_types: string[];
  trend: { procedure_id: string; score: number; created_at: string | null }[];
}

export interface AskResponse {
  question: string;
  answer: string;
  provider: string;
  cited_cases: SimilarCase[];
}
