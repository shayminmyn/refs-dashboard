// Luôn dùng relative URL — Next.js rewrite (/api/*) proxy đến backend nội bộ.
// Không dùng NEXT_PUBLIC_API_URL ở client vì Docker internal hostname không
// thể resolve từ browser.
const API_BASE = '';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { message?: string }).message ?? `HTTP ${res.status}`);
  }

  return res.json();
}

function buildQuery(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '');
  if (entries.length === 0) return '';
  const qs = new URLSearchParams(entries as [string, string][]).toString();
  return `?${qs}`;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; username: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<{ username: string }>('/api/auth/me'),

  getExchanges: () =>
    request<Exchange[]>('/api/exchanges'),

  getUsers: (params: UsersParams) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '') as [string, string][]
    ).toString();
    return request<UsersResponse>(`/api/users?${qs}`);
  },

  getOverviewStats: (from?: string, to?: string) =>
    request<OverviewStats>(`/api/stats/overview${buildQuery({ from, to })}`),

  getExchangeStats: (exchangeId: string, from?: string, to?: string) =>
    request<ExchangeStats>(`/api/stats/${exchangeId}${buildQuery({ from, to })}`),

  getTimeseries: (exchangeId: string, metric: string, period: string, from?: string, to?: string) =>
    request<TimeseriesPoint[]>(
      `/api/stats/${exchangeId}/timeseries${buildQuery({ metric, period, from, to })}`,
    ),

  getSyncLogs: (exchangeId?: string) =>
    request<SyncLog[]>(`/api/sync/logs${exchangeId ? `?exchange=${exchangeId}` : ''}`),

  triggerSync: (exchangeId: string) =>
    request<{ success: boolean; recordsUpserted: number }>(`/api/sync/${exchangeId}`, { method: 'POST' }),

  // ── Community Members ──────────────────────────────────────────────────────
  getMembers: (params: MembersParams) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '') as [string, string][]
    ).toString();
    return request<MembersResponse>(`/api/members${qs ? `?${qs}` : ''}`);
  },

  getMember: (id: string) =>
    request<CommunityMember>(`/api/members/${id}`),

  createMember: (body: MemberCreatePayload) =>
    request<CommunityMember>('/api/members', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateMember: (id: string, body: MemberUpdatePayload) =>
    request<CommunityMember>(`/api/members/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  deleteMember: (id: string) =>
    request<void>(`/api/members/${id}`, { method: 'DELETE' }),

  addExchangeLink: (memberId: string, link: ExchangeLinkPayload) =>
    request<CommunityMember>(`/api/members/${memberId}/links`, {
      method: 'POST',
      body: JSON.stringify(link),
    }),

  removeExchangeLink: (memberId: string, exchangeId: string, exchangeUserId: string) =>
    request<void>(`/api/members/${memberId}/links/${exchangeId}/${exchangeUserId}`, { method: 'DELETE' }),

  getMemberStats: (memberId: string) =>
    request<MemberStats>(`/api/members/${memberId}/stats`),

  lookupExchangeUser: (exchangeId: string, exchangeUserId: string) =>
    request<ReferredUser>(`/api/members/lookup/${exchangeId}/${exchangeUserId}`),

  // ── Trading signals (MongoDB trading.signals) ──────────────────────────────
  getSignals: (params: SignalsListParams) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '') as [string, string][]
    ).toString();
    return request<SignalsListResponse>(`/api/signals${qs ? `?${qs}` : ''}`);
  },

  getSignalStats: (params: SignalsFilterParams) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '') as [string, string][]
    ).toString();
    return request<SignalStats>(`/api/signals/stats${qs ? `?${qs}` : ''}`);
  },

  getSignalFilters: (params: SignalsFilterParams) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '') as [string, string][]
    ).toString();
    return request<SignalsFiltersResponse>(`/api/signals/filters${qs ? `?${qs}` : ''}`);
  },
};

export interface Exchange {
  id: string;
  name: string;
  logoUrl: string;
  color: string;
  enabled: boolean;
  cronSchedule: string;
}

export interface ReferredUser {
  _id: string;
  exchangeId: string;
  userId: string;
  username: string;
  email: string;
  registeredAt: string;
  totalDeposit: number;
  totalVolume: number;
  totalCommission: number;
  status: 'active' | 'inactive';
  lastSyncedAt: string;
}

export interface UsersParams {
  exchange?: string;
  page?: string;
  limit?: string;
  search?: string;
  from?: string;
  to?: string;
  status?: string;
  sortBy?: string;
  sortDir?: string;
}

export interface UsersResponse {
  data: ReferredUser[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface ExchangeStats {
  totalDeposit: number;
  totalVolume: number;
  totalCommission: number;
  totalUsers: number;
  activeUsers: number;
}

export interface OverviewStats {
  totals: ExchangeStats;
  byExchange: Array<ExchangeStats & {
    exchangeId: string;
    exchangeName: string;
    color: string;
  }>;
}

export interface TimeseriesPoint {
  date: string;
  value: number;
  count: number;
}

export interface SyncLog {
  _id: string;
  exchangeId: string;
  startedAt: string;
  finishedAt: string | null;
  status: 'running' | 'success' | 'failed';
  recordsUpserted: number;
  error: string | null;
}

// ── Community Members ──────────────────────────────────────────────────────

export type Platform = 'telegram' | 'discord' | 'other';

export interface ExchangeLink {
  exchangeId: string;
  exchangeUserId: string;
  note: string;
  linkedAt: string;
}

export interface CommunityMember {
  _id: string;
  platform: Platform;
  platformId: string;
  username: string;
  fullName: string;
  phone: string;
  notes: string;
  tags: string[];
  isActive: boolean;
  exchangeLinks: ExchangeLink[];
  createdAt: string;
  updatedAt: string;
}

export interface MembersParams {
  platform?: string;
  search?: string;
  exchange?: string;
  isActive?: string;
  page?: string;
  limit?: string;
  sortBy?: string;
  sortDir?: string;
}

export interface MembersResponse {
  data: CommunityMember[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface MemberCreatePayload {
  platform: Platform;
  platform_id: string;
  username?: string;
  full_name?: string;
  phone?: string;
  notes?: string;
  tags?: string[];
  exchange_links?: ExchangeLinkPayload[];
}

export interface MemberUpdatePayload {
  username?: string;
  full_name?: string;
  phone?: string;
  notes?: string;
  tags?: string[];
  is_active?: boolean;
}

export interface ExchangeLinkPayload {
  exchange_id: string;
  exchange_user_id: string;
  note?: string;
}

export interface MemberStatsLink {
  exchangeId: string;
  exchangeUserId: string;
  note: string;
  totalDeposit: number;
  totalVolume: number;
  totalCommission: number;
  status: string;
  exchangeUsername: string;
}

export interface MemberStats {
  totalDeposit: number;
  totalVolume: number;
  totalCommission: number;
  links: MemberStatsLink[];
}

// ── Trading signals ──────────────────────────────────────────────────────────

export interface SignalsFilterParams {
  from?: string;
  to?: string;
  symbol?: string;
  strategy?: string;
  timeframe?: string;
  status?: string;
}

export interface SignalsListParams extends SignalsFilterParams {
  page?: string;
  limit?: string;
  sortDir?: string;
}

export interface SignalStats {
  totalSignals: number;
  closedTrades: number;
  wins: number;
  losses: number;
  breakeven: number;
  unsettledR: number;
  winRate: number | null;
  totalR: number;
  avgR: number | null;
  /** Σ (risk% trên 1R × realized_r) — % equity cộng dồn gần đúng */
  totalReturnPct: number;
  /** Σ (risk% trên 1R × rr_ratio) — stack % nếu mỗi lệnh chốt đủ RR khai báo */
  totalTargetRrPct: number;
  tradesWithRiskPct: number;
  avgReturnPct: number | null;
}

export interface SignalRow {
  _id: string;
  orderType: string | null;
  symbol: string | null;
  strategy: string | null;
  timeframe: string | null;
  status: string | null;
  signalKey: string | null;
  comment: string | null;
  exitReason: string | null;
  rrRatio: number | null;
  riskPercent: number | null;
  realizedR: number | null;
  closedAt: string | null;
  signalAt: string | null;
  entryPrice: number | null;
  stopLoss: number | null;
  isClosed: boolean;
}

export interface SignalsListResponse {
  data: SignalRow[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface SignalsFiltersResponse {
  symbols: string[];
  strategies: string[];
  timeframes: string[];
  statuses: string[];
}
