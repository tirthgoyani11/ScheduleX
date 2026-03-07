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
  lecture_hours: number;
  lab_hours: number;
  needs_lab: boolean;
  batch_size: number;
  batch: string | null;
  created_at: string;
}

// ── Batch ────────────────────────────────────────────────
export interface Batch {
  batch_id: string;
  dept_id: string;
  semester: number;
  name: string;
  size: number;
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
export type TimetableStatus = "draft" | "published" | "deleted" | "DRAFT" | "PUBLISHED" | "DELETED";

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

export interface SemesterResult {
  semester: number;
  timetable_id?: string;
  status: string;
  score?: number;
  entry_count: number;
  wall_time: number;
  error?: string;
}

export interface GenerateAllResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: SemesterResult[];
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

// ── Time Slots (configurable per college, stored in backend) ──
export interface TimeSlot {
  slot_id: string;
  college_id: string;
  slot_order: number;
  label: string;
  start_time: string;   // "HH:MM"
  end_time: string;      // "HH:MM"
  slot_type: "lecture" | "lab" | "break";
}

// ── Scheduling (Reschedule / Proxy / Extra Lecture) ──────────
export type BookingType = "reschedule" | "extra_lecture" | "proxy";
export type BookingStatus = "pending" | "approved" | "rejected" | "cancelled";

export interface FreeSlot {
  day: string;
  period: number;
  slot_label: string;
  start_time: string;
  end_time: string;
}

export interface FreeSlotWithRooms {
  day: string;
  period: number;
  slot_label: string;
  start_time: string;
  end_time: string;
  free_rooms: FreeRoom[];
}

export interface FreeRoom {
  room_id: string;
  room_name: string;
  room_type: string;
  capacity: number;
}

export interface FreeFaculty {
  faculty_id: string;
  name: string;
  expertise: string[];
  current_load: number;
  max_weekly_load: number;
}

export interface SlotBooking {
  booking_id: string;
  booking_type: BookingType;
  status: BookingStatus;
  faculty_name: string;
  subject_name: string;
  day: string;
  period: number;
  room_name: string;
  target_date: string | null;
  reason: string | null;
  requested_by_name: string;
  created_at: string;
}

export interface BusyFaculty {
  faculty_id: string;
  name: string;
  reason: string;
}

export interface DateSlotCheck {
  period: number;
  slot_label: string;
  start_time: string;
  end_time: string;
  free_rooms: FreeRoom[];
  busy_rooms: FreeRoom[];
  free_faculty: FreeFaculty[];
  busy_faculty: BusyFaculty[];
}

export interface DateCheckResult {
  date: string;
  day_of_week: string;
  slots: DateSlotCheck[];
}

// Legacy helper — period number from slot_order, display times
export const DEFAULT_TIME_SLOTS: TimeSlot[] = [
  { slot_id: "", college_id: "", slot_order: 1, label: "Period 1", start_time: "09:00", end_time: "10:00", slot_type: "lecture" },
  { slot_id: "", college_id: "", slot_order: 2, label: "Period 2", start_time: "10:00", end_time: "11:00", slot_type: "lecture" },
  { slot_id: "", college_id: "", slot_order: 3, label: "Period 3", start_time: "11:00", end_time: "12:00", slot_type: "lecture" },
  { slot_id: "", college_id: "", slot_order: 4, label: "Period 4", start_time: "12:00", end_time: "13:00", slot_type: "lecture" },
  { slot_id: "", college_id: "", slot_order: 5, label: "Lunch",    start_time: "13:00", end_time: "14:00", slot_type: "break" },
  { slot_id: "", college_id: "", slot_order: 6, label: "Period 5", start_time: "14:00", end_time: "15:00", slot_type: "lecture" },
  { slot_id: "", college_id: "", slot_order: 7, label: "Lab 1",    start_time: "15:00", end_time: "17:00", slot_type: "lab" },
  { slot_id: "", college_id: "", slot_order: 8, label: "Lab 2",    start_time: "17:00", end_time: "19:00", slot_type: "lab" },
];
