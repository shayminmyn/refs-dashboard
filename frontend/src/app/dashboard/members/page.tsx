'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  api,
  CommunityMember,
  Exchange,
  MemberCreatePayload,
  MemberUpdatePayload,
  Platform,
  MembersParams,
} from '@/lib/api';
import Header from '@/components/layout/Header';
import {
  Users,
  Plus,
  Search,
  Send,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  X,
  Loader2,
  Pencil,
} from 'lucide-react';

const PLATFORM_LABELS: Record<Platform, string> = {
  telegram: 'Telegram',
  discord: 'Discord',
  other: 'Other',
};
const PLATFORM_COLORS: Record<Platform, string> = {
  telegram: 'text-sky-400',
  discord: 'text-violet-400',
  other: 'text-muted-foreground',
};

// ── Shared field styles ───────────────────────────────────────────────────────
const inputCls =
  'mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground';

// ── Create modal ──────────────────────────────────────────────────────────────

function MemberFormModal({
  title,
  initial,
  onClose,
  onSave,
}: {
  title: string;
  initial?: Partial<{
    platform: Platform;
    platformId: string;
    username: string;
    fullName: string;
    phone: string;
    notes: string;
    tags: string[];
    isActive: boolean;
  }>;
  onClose: () => void;
  onSave: (payload: MemberCreatePayload | MemberUpdatePayload) => Promise<void>;
}) {
  const isEdit = !!initial?.platformId;

  const [platform, setPlatform] = useState<Platform>(initial?.platform ?? 'telegram');
  const [platformId, setPlatformId] = useState(initial?.platformId ?? '');
  const [username, setUsername] = useState(initial?.username ?? '');
  const [fullName, setFullName] = useState(initial?.fullName ?? '');
  const [phone, setPhone] = useState(initial?.phone ?? '');
  const [notes, setNotes] = useState(initial?.notes ?? '');
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>(initial?.tags ?? []);
  const [isActive, setIsActive] = useState(initial?.isActive ?? true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function addTag() {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) setTags((prev) => [...prev, t]);
    setTagInput('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isEdit && !platformId.trim()) { setError('Platform ID là bắt buộc'); return; }
    setError('');
    setLoading(true);
    try {
      if (isEdit) {
        const payload: MemberUpdatePayload = {
          username: username.trim(),
          full_name: fullName.trim(),
          phone: phone.trim(),
          notes: notes.trim(),
          tags,
          is_active: isActive,
        };
        await onSave(payload);
      } else {
        const payload: MemberCreatePayload = {
          platform,
          platform_id: platformId.trim(),
          username: username.trim(),
          full_name: fullName.trim(),
          phone: phone.trim(),
          notes: notes.trim(),
          tags,
        };
        await onSave(payload);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Thao tác thất bại');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-card border border-border rounded-xl w-full max-w-lg shadow-2xl my-4">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <p className="text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">{error}</p>
          )}

          {/* Platform — chỉ hiện khi tạo mới */}
          {!isEdit && (
            <div>
              <label className="text-xs font-medium text-muted-foreground">Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value as Platform)}
                className={inputCls}
              >
                {(Object.keys(PLATFORM_LABELS) as Platform[]).map((p) => (
                  <option key={p} value={p}>{PLATFORM_LABELS[p]}</option>
                ))}
              </select>
            </div>
          )}

          {/* Platform ID — chỉ khi tạo mới */}
          {!isEdit && (
            <div>
              <label className="text-xs font-medium text-muted-foreground">
                Platform ID <span className="text-destructive">*</span>
              </label>
              <input
                value={platformId}
                onChange={(e) => setPlatformId(e.target.value)}
                placeholder={platform === 'telegram' ? 'Telegram user_id (số)' : 'ID trên platform'}
                className={inputCls}
              />
            </div>
          )}

          {/* Username + Họ tên */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Username</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={platform === 'telegram' ? '@username' : 'username'}
                className={inputCls}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Họ tên</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Tên thật"
                className={inputCls}
              />
            </div>
          </div>

          {/* Số điện thoại */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Số điện thoại</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+84..."
              className={inputCls}
            />
          </div>

          {/* Tags */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tags</label>
            <div className="flex gap-2 mt-1">
              <input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
                placeholder="Nhập tag rồi nhấn Enter"
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
              />
              <button type="button" onClick={addTag}
                className="px-3 py-2 bg-secondary rounded-lg text-xs text-muted-foreground hover:text-foreground">
                Thêm
              </button>
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {tags.map((t) => (
                  <span key={t} className="flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs">
                    {t}
                    <button type="button" onClick={() => setTags(tags.filter((x) => x !== t))}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Ghi chú */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Ghi chú</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Ghi chú nội bộ..."
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground resize-none"
            />
          </div>

          {/* Active toggle — chỉ khi sửa */}
          {isEdit && (
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Trạng thái</span>
              <button
                type="button"
                onClick={() => setIsActive((v) => !v)}
                className={`relative w-11 h-6 rounded-full transition-colors ${isActive ? 'bg-emerald-500' : 'bg-secondary border border-border'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${isActive ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
              <span className={`text-xs ml-2 ${isActive ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                {isActive ? 'Active' : 'Inactive'}
              </span>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground bg-secondary rounded-lg">
              Huỷ
            </button>
            <button type="submit" disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-60">
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {isEdit ? 'Lưu thay đổi' : 'Tạo member'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MembersPage() {
  const [members, setMembers] = useState<CommunityMember[]>([]);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<CommunityMember | null>(null);

  const [search, setSearch] = useState('');
  const [filterExchange, setFilterExchange] = useState('');
  const [filterPlatform, setFilterPlatform] = useState('');

  const load = useCallback(async (params: MembersParams) => {
    setLoading(true);
    try {
      const res = await api.getMembers(params);
      setMembers(res.data);
      setTotal(res.pagination.total);
      setTotalPages(res.pagination.totalPages);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.getExchanges().then(setExchanges);
  }, []);

  useEffect(() => {
    load({
      search: search || undefined,
      exchange: filterExchange || undefined,
      platform: filterPlatform || undefined,
      page: String(page),
      limit: '20',
    });
  }, [search, filterExchange, filterPlatform, page, load]);

  async function handleCreate(payload: MemberCreatePayload | MemberUpdatePayload) {
    const created = await api.createMember(payload as MemberCreatePayload);
    setShowCreate(false);
    setMembers((prev) => [created, ...prev]);
    setTotal((t) => t + 1);
  }

  async function handleEdit(payload: MemberCreatePayload | MemberUpdatePayload) {
    if (!editTarget) return;
    const updated = await api.updateMember(editTarget._id, payload as MemberUpdatePayload);
    setEditTarget(null);
    setMembers((prev) => prev.map((m) => (m._id === updated._id ? updated : m)));
  }

  return (
    <>
      <Header title="Community Members" subtitle="Quản lý thành viên cộng đồng (Telegram...)" />
      <div className="flex-1 p-6 space-y-5">

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-52">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Tìm theo tên, username, platform ID, tag..."
              className="w-full rounded-lg border border-border bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
            />
          </div>

          <select value={filterPlatform} onChange={(e) => { setFilterPlatform(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground">
            <option value="">All platforms</option>
            {(Object.keys(PLATFORM_LABELS) as Platform[]).map((p) => (
              <option key={p} value={p}>{PLATFORM_LABELS[p]}</option>
            ))}
          </select>

          <select value={filterExchange} onChange={(e) => { setFilterExchange(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground">
            <option value="">All exchanges</option>
            {exchanges.map((ex) => (
              <option key={ex.id} value={ex.id}>{ex.name}</option>
            ))}
          </select>

          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Add Member
          </button>
        </div>

        {/* Stats bar */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Users className="w-3.5 h-3.5" />
          <span>{total} members</span>
        </div>

        {/* Table */}
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {['Platform', 'Username / Họ tên', 'Platform ID', 'Điện thoại', 'Tags', 'Sàn', 'Trạng thái', 'Hành động'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 8 }).map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-secondary animate-pulse rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : members.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                      Chưa có member nào
                    </td>
                  </tr>
                ) : (
                  members.map((m) => (
                    <tr key={m._id} className="hover:bg-accent/40 transition-colors">
                      <td className="px-4 py-3">
                        <span className={`flex items-center gap-1.5 text-xs font-medium ${PLATFORM_COLORS[m.platform]}`}>
                          {m.platform === 'telegram' && <Send className="w-3.5 h-3.5" />}
                          {PLATFORM_LABELS[m.platform]}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">
                          {m.username ? `@${m.username}` : <span className="text-muted-foreground">—</span>}
                        </p>
                        {m.fullName && (
                          <p className="text-xs text-muted-foreground">{m.fullName}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        {m.platformId}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {m.phone || '—'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {m.tags.length > 0
                            ? m.tags.map((t) => (
                                <span key={t} className="px-1.5 py-0.5 bg-secondary text-muted-foreground rounded text-xs">
                                  {t}
                                </span>
                              ))
                            : <span className="text-muted-foreground text-xs">—</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {m.exchangeLinks.length > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-400/10 text-emerald-400 rounded-full">
                            {m.exchangeLinks.length} sàn
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          m.isActive
                            ? 'bg-emerald-400/10 text-emerald-400'
                            : 'bg-secondary text-muted-foreground'
                        }`}>
                          {m.isActive ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => setEditTarget(m)}
                            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                            Sửa
                          </button>
                          <Link href={`/dashboard/members/${m._id}`}
                            className="flex items-center gap-1 text-xs text-primary hover:underline">
                            <ExternalLink className="w-3.5 h-3.5" />
                            Chi tiết
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Trang {page} / {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="p-1.5 rounded border border-border text-muted-foreground hover:text-foreground disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1.5 rounded border border-border text-muted-foreground hover:text-foreground disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create modal */}
      {showCreate && (
        <MemberFormModal
          title="Thêm Community Member"
          onClose={() => setShowCreate(false)}
          onSave={handleCreate}
        />
      )}

      {/* Edit modal */}
      {editTarget && (
        <MemberFormModal
          title={`Chỉnh sửa: ${editTarget.username ? '@' + editTarget.username : editTarget.platformId}`}
          initial={{
            platform: editTarget.platform,
            platformId: editTarget.platformId,
            username: editTarget.username,
            fullName: editTarget.fullName,
            phone: editTarget.phone,
            notes: editTarget.notes,
            tags: editTarget.tags,
            isActive: editTarget.isActive,
          }}
          onClose={() => setEditTarget(null)}
          onSave={handleEdit}
        />
      )}
    </>
  );
}
