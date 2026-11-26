const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');

export type Category = 'pothole' | 'streetlight' | 'garbage' | 'graffiti' | 'sidewalk' | 'signage' | 'drainage' | 'other';
export type Status = 'open' | 'closed' | 'merged';

export interface Incident {
  id: string;
  title: string;
  description: string;
  category: Category;
  latitude: number;
  longitude: number;
  status: Status;
  merged_into_incident_id?: string | null;
  created_at: string;
  updated_at: string;
  reports?: Report[];
}

export interface IncidentMapItem {
  id: string;
  title: string;
  description: string;
  category: Category;
  latitude: number;
  longitude: number;
  status: Status;
  report_count: number;
  created_at: string;
}

export interface Report {
  id: string;
  description: string;
  category: Category;
  latitude: number;
  longitude: number;
  image_path: string;
  sha256_hash: string | null;
  phash: string;
  phash_size: number | null;
  created_at: string;
  incident_id: string;
  incident?: Incident | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export type MatchingJobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type SuggestionStatus = 'pending' | 'reviewed' | 'dismissed' | 'rejected' | 'auto_merged' | 'superseded';

export type MatchingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface MatchSuggestion {
  id: string;
  report_id: string;
  incident_id: string;
  matched_report_id: string;
  similarity_score: number;
  status: SuggestionStatus;
  created_at: string;
  incident_title: string | null;
  incident_category: Category | null;
  incident_status: Status | null;
  incident_latitude: number | null;
  incident_longitude: number | null;
  matched_report_description: string | null;
  sha256_match: boolean | null;
  phash_hamming_distance: number | null;
  phash_similarity: number | null;
  text_similarity: number | null;
  geo_distance_meters: number | null;
  category_match: boolean | null;
  candidate_classification: 'AUTO_MERGE_CANDIDATE' | 'REVIEW_CANDIDATE' | 'NO_MATCH' | null;
}

export interface PublicMatchingStatus {
  status: MatchingStatus;
  suggestion_count: number;
  error_message: string | null;
}

export interface MatchingJob {
  id: string;
  report_id: string;
  status: MatchingJobStatus;
  error_message: string | null;
  attempts: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  suggestions: MatchSuggestion[];
}

export interface AIHealthResponse {
  status: 'not_loaded' | 'loading' | 'ready' | 'failed' | 'disabled';
  model_name: string;
  error: string | null;
  semantic_matching_enabled: boolean;
}

export interface AdminSession {
  authenticated: boolean;
  username: string | null;
  csrf_token?: string | null;
}

export interface AdminLoginResponse {
  authenticated: boolean;
  username: string;
  csrf_token: string;
}

export interface DashboardStats {
  total_reports: number;
  total_incidents: number;
  open_incidents: number;
  closed_incidents: number;
  merged_incidents: number;
  pending_suggestions: number;
  pending_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  reports_last_7_days: number;
}

export interface RecentReport {
  id: string;
  category: Category;
  description: string;
  created_at: string;
  incident_id: string | null;
  image_path: string | null;
}

export interface AdminIncidentListItem extends Incident {
  report_count: number;
}

export interface AdminReportListItem extends Report {
  incident_status: Status | null;
  matching_job_status: MatchingJobStatus | null;
}

export interface AdminReportDetail extends AdminReportListItem {
  incident: Incident | null;
  matching_job: MatchingJob | null;
  match_suggestions: MatchSuggestion[];
}

export interface AdminReportDeleteResponse {
  deleted: boolean;
  report_id: string;
  incident_deleted: boolean;
  image_deleted: boolean;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg).join(', ');
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const CSRF_COOKIE_NAME = 'streetproof_csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';
let csrfTokenCache: string | null = null;

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|;\s*)${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setCsrfToken(token: string | null | undefined): void {
  csrfTokenCache = token?.trim() ? token.trim() : null;
}

export function getCsrfToken(): string | null {
  const cookieToken = readCookie(CSRF_COOKIE_NAME);
  if (cookieToken) {
    csrfTokenCache = cookieToken;
    return cookieToken;
  }
  return csrfTokenCache;
}

function csrfHeaders(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { [CSRF_HEADER_NAME]: token } : {};
}

async function handleAdminAuthResponse<T extends { csrf_token?: string | null }>(response: Response): Promise<T> {
  const data = await handleResponse<T>(response);
  if (data && typeof data === 'object' && 'csrf_token' in data) {
    setCsrfToken(data.csrf_token);
  }
  return data;
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<HealthResponse>(response);
}

export async function submitReport(formData: FormData): Promise<Report> {
  const response = await fetch(`${API_BASE_URL}/api/reports`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<Report>(response);
}

export async function getReports(page = 1, pageSize = 20): Promise<PaginatedResponse<Report>> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const response = await fetch(`${API_BASE_URL}/api/reports?${params.toString()}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PaginatedResponse<Report>>(response);
}

export async function getReport(id: string): Promise<Report> {
  const response = await fetch(`${API_BASE_URL}/api/reports/${id}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Report>(response);
}

export async function getIncidents(page = 1, pageSize = 20): Promise<PaginatedResponse<Incident>> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const response = await fetch(`${API_BASE_URL}/api/incidents?${params.toString()}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PaginatedResponse<Incident>>(response);
}

export async function getIncident(id: string): Promise<Incident> {
  const response = await fetch(`${API_BASE_URL}/api/incidents/${id}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Incident>(response);
}

export async function getIncidentsForMap(): Promise<IncidentMapItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/incidents/map`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IncidentMapItem[]>(response);
}

export async function getMatchingStatus(reportId: string): Promise<PublicMatchingStatus | null> {
  const response = await fetch(`${API_BASE_URL}/api/matching/reports/${reportId}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PublicMatchingStatus | null>(response);
}

export async function getAIHealth(): Promise<AIHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health/ai`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<AIHealthResponse>(response);
}

export async function adminLogin(username: string, password: string): Promise<AdminLoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return handleAdminAuthResponse<AdminLoginResponse>(response);
}

export async function adminLogout(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...csrfHeaders(),
      },
    });
    return await handleResponse<void>(response);
  } finally {
    setCsrfToken(null);
  }
}

export async function getAdminSession(): Promise<AdminSession> {
  const response = await fetch(`${API_BASE_URL}/api/admin/session`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleAdminAuthResponse<AdminSession>(response);
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_BASE_URL}/api/admin/dashboard/stats`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<DashboardStats>(response);
}

export async function getRecentReports(): Promise<RecentReport[]> {
  const response = await fetch(`${API_BASE_URL}/api/admin/dashboard/recent-reports`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<RecentReport[]>(response);
}

export interface AdminReportsParams {
  page?: number;
  page_size?: number;
  search?: string;
  category?: Category;
  status?: Status;
}

export async function getAdminReports(params: AdminReportsParams = {}): Promise<PaginatedResponse<AdminReportListItem>> {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  if (params.search) q.set('search', params.search);
  if (params.category) q.set('category', params.category);
  if (params.status) q.set('status', params.status);
  const response = await fetch(`${API_BASE_URL}/api/admin/reports?${q.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PaginatedResponse<AdminReportListItem>>(response);
}

export async function getAdminReport(reportId: string): Promise<AdminReportDetail> {
  const response = await fetch(`${API_BASE_URL}/api/admin/reports/${reportId}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<AdminReportDetail>(response);
}

export async function getAdminIncidents(page = 1, pageSize = 20, status?: Status): Promise<PaginatedResponse<AdminIncidentListItem>> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  const response = await fetch(`${API_BASE_URL}/api/admin/incidents?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PaginatedResponse<AdminIncidentListItem>>(response);
}

export async function getAdminIncident(incidentId: string): Promise<Incident> {
  const response = await fetch(`${API_BASE_URL}/api/admin/incidents/${incidentId}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Incident>(response);
}

export async function updateAdminIncidentStatus(incidentId: string, status: 'open' | 'closed'): Promise<Incident> {
  const response = await fetch(`${API_BASE_URL}/api/admin/incidents/${incidentId}/status`, {
    method: 'PATCH',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...csrfHeaders(),
    },
    body: JSON.stringify({ status }),
  });
  return handleResponse<Incident>(response);
}

export async function deleteAdminReport(reportId: string): Promise<AdminReportDeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/reports/${reportId}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...csrfHeaders(),
    },
  });
  return handleResponse<AdminReportDeleteResponse>(response);
}

export function imageUrl(imagePath: string): string {
  if (!imagePath) return '';
  // Production/Supabase stores full public URL; keep absolute URLs unchanged.
  if (/^https?:\/\//i.test(imagePath)) return imagePath;
  // Legacy/local: "uploads/<file>" or bare filename served from backend /uploads.
  const clean = imagePath.replace(/^\/+/, '');
  if (clean.startsWith('uploads/')) {
    return `${API_BASE_URL}/${clean}`;
  }
  return `${API_BASE_URL}/uploads/${clean}`;
}

export { API_BASE_URL };
export interface AdminMatchReport {
  id: string;
  description: string;
  category: Category;
  latitude: number;
  longitude: number;
  image_path: string;
  created_at: string;
  incident_id: string;
  incident_status: Status | null;
}

export interface AdminMatchSuggestionListItem {
  id: string;
  report_id: string;
  incident_id: string;
  matched_report_id: string;
  similarity_score: number;
  status: SuggestionStatus;
  candidate_classification: string | null;
  created_at: string;
  sha256_match: boolean | null;
  phash_hamming_distance: number | null;
  phash_similarity: number | null;
  text_similarity: number | null;
  geo_distance_meters: number | null;
  category_match: boolean | null;
  report: AdminMatchReport;
  matched_report: AdminMatchReport;
  incident_title: string | null;
}

export interface AdminMatchSuggestionDetail extends AdminMatchSuggestionListItem {
  merge_event_id: string | null;
  merge_execution_status: string | null;
  merge_execution_error: string | null;
  reversible: boolean;
}

export interface AdminMatchesParams {
  page?: number;
  page_size?: number;
  status?: SuggestionStatus;
  search?: string;
  category?: Category;
  classification?: string;
}

export interface MergeEventListItem {
  id: string;
  source_incident_id: string | null;
  target_incident_id: string;
  report_id: string;
  matched_report_id: string | null;
  action: string;
  actor: string;
  candidate_classification: string;
  heuristic_score: number | null;
  created_at: string;
  reversed_at: string | null;
}

export async function getAdminMatches(params: AdminMatchesParams = {}): Promise<PaginatedResponse<AdminMatchSuggestionListItem>> {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  if (params.status) q.set('status', params.status);
  if (params.search) q.set('search', params.search);
  if (params.category) q.set('category', params.category);
  if (params.classification) q.set('classification', params.classification);
  const response = await fetch(`${API_BASE_URL}/api/admin/matches?${q.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PaginatedResponse<AdminMatchSuggestionListItem>>(response);
}

export async function getAdminMatch(suggestionId: string): Promise<AdminMatchSuggestionDetail> {
  const response = await fetch(`${API_BASE_URL}/api/admin/matches/${suggestionId}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<AdminMatchSuggestionDetail>(response);
}

export async function acceptAdminMatch(suggestionId: string): Promise<{ suggestion_id: string; status: SuggestionStatus; merge_event_id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/admin/matches/${suggestionId}/accept`, {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json', ...csrfHeaders() },
  });
  return handleResponse(response);
}

export async function rejectAdminMatch(suggestionId: string, reason?: string): Promise<{ suggestion_id: string; status: SuggestionStatus }> {
  const response = await fetch(`${API_BASE_URL}/api/admin/matches/${suggestionId}/reject`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...csrfHeaders() },
    body: JSON.stringify({ reason: reason ?? null }),
  });
  return handleResponse(response);
}

export async function getAdminMergeEvents(page = 1, pageSize = 20): Promise<PaginatedResponse<MergeEventListItem>> {
  const q = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const response = await fetch(`${API_BASE_URL}/api/admin/merges?${q.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<PaginatedResponse<MergeEventListItem>>(response);
}

export async function reverseAdminMerge(mergeEventId: string): Promise<MergeEventListItem> {
  const response = await fetch(`${API_BASE_URL}/api/admin/merges/${mergeEventId}/reverse`, {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json', ...csrfHeaders() },
  });
  return handleResponse<MergeEventListItem>(response);
}
