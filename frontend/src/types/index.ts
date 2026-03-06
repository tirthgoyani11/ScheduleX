// ── Auth ─────────────────────────────────────────────────
export type UserRole = "super_admin" | "dept_admin" | "faculty";

export interface User {
  user_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  college_id: string;
  dept_id: string | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  role: string;
  full_name: string;
  college_id: string;
  dept_id: string | null;
}

// ── College & Department ─────────────────────────────────
export interface College {
  college_id: string;
  name: string;
  affiliation: string;
  city: string;
  created_at: string;
}

export interface Department {
  dept_id: string;
  college_id: string;
  name: string;
  code: string;
  created_at: string;
}

// ── Faculty ──────────────────────────────────────────────
export interface Faculty {
  faculty_id: string;
  dept_id: string;
  name: string;
  employee_id: string;
  expertise: string[];
  max_weekly_load: number;
  preferred_time: string | null;
  substitution_count: number;
  last_substitution_date: string | null;
  created_at: string;
}

// ── Subject ──────────────────────────────────────────────
export interface Subject {
  subject_id: string;
  dept_id: string;
  name: string;
  subject_code: string;
  semester: number;
  credits: number;
  weekly_periods: number;
  needs_lab: boolean;
  batch_size: number;
  batch: string | null;
  created_at: string;
}

// ── Room ─────────────────────────────────────────────────
export type RoomType = "classroom" | "lab" | "seminar";

export interface Room {
  room_id: string;
  college_id: string;
  name: string;
  capacity: number;
  room_type: RoomType;
  has_projector: boolean;
  has_computers: boolean;
  has_ac: boolean;
}

// ── Timetable ────────────────────────────────────────────
export type TimetableStatus = "DRAFT" | "PUBLISHED" | "DELETED";

export interface TimetableEntry {
  entry_id: string;
  day: string;
  period: number;
  subject_name: string;
  faculty_name: string;
  room_name: string;
  entry_type: string;
  batch: string | null;
}

export interface Timetable {
  timetable_id: string;
  semester: number;
  academic_year: string;
  status: TimetableStatus;
  optimization_score: number | null;
  entries: TimetableEntry[];
  created_at: string;
  published_at: string | null;
}

export interface JobResponse {
  job_id: string;
  timetable_id: string;
  status: string;
}

// ── Analytics ────────────────────────────────────────────
export interface DashboardStats {
  faculty_count: number;
  timetable_count: number;
  subject_count: number;
  room_count: number;
}

export interface FacultyLoad {
  faculty_id: string;
  name: string;
  max_weekly_load: number;
  assigned_periods: number;
  utilisation_pct: number;
}

export interface RoomUtilisation {
  room_id: string;
  name: string;
  capacity: number;
  booked_slots: number;
  total_slots: number;
  utilisation_pct: number;
}

// ── Notification ─────────────────────────────────────────
export interface Notification {
  log_id: string;
  event_type: string;
  channel: string;
  message_body: string;
  status: string;
  sent_at: string;
  delivered_at: string | null;
}

// ── Substitution ─────────────────────────────────────────
export interface SubstitutionCandidate {
  faculty_id: string;
  name: string;
  score: number;
  expertise_match: boolean;
  load_headroom_pct: number;
  days_since_last_sub: number;
  preferred_time: string | null;
}

// ── Time Slots (display only, periods are 1-8 in backend) ──
export interface TimeSlot {
  period: number;
  label: string;
  startTime: string;
  endTime: string;
  type: "LECTURE" | "LAB";
}

// Default time slots for display (configurable per college)
export const DEFAULT_TIME_SLOTS: TimeSlot[] = [
  { period: 1, label: "Period 1", startTime: "09:00", endTime: "10:00", type: "LECTURE" },
  { period: 2, label: "Period 2", startTime: "10:00", endTime: "11:00", type: "LECTURE" },
  { period: 3, label: "Period 3", startTime: "11:00", endTime: "12:00", type: "LECTURE" },
  { period: 4, label: "Period 4", startTime: "12:00", endTime: "13:00", type: "LECTURE" },
  { period: 5, label: "Lunch", startTime: "13:00", endTime: "14:00", type: "LECTURE" },
  { period: 6, label: "Period 5", startTime: "14:00", endTime: "15:00", type: "LECTURE" },
  { period: 7, label: "Lab 1", startTime: "15:00", endTime: "17:00", type: "LAB" },
  { period: 8, label: "Lab 2", startTime: "17:00", endTime: "19:00", type: "LAB" },
];
