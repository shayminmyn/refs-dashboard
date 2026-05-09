'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  api,
  CommunityMember,
  Exchange,
  ExchangeLinkPayload,
  MemberStats,
  MemberUpdatePayload,
} from '@/lib/api';
import Header from '@/components/layout/Header';
import { formatCurrency } from '@/lib/utils';
import {
  Send,
  Pencil,
  Trash2,
  Plus,
  X,
  Loader2,
  Link2,
  TrendingUp,
  Wallet,
  DollarSign,
  ArrowLeft,
  Check,
} from 'lucide-react';
import Link from 'next/link';

// ── Add-link modal ────────────────────────────────────────────────────────────

function AddLinkModal({
  exchanges,
  onClose,
  onLinked,
}: {
  exchanges: Exchange[];
  onClose: () => void;
  onLinked: (link: ExchangeLinkPayload & { displayName?: string }) => void;
}) {
  const [exchangeId, setExchangeId] = useState(exchanges[0]?.id ?? '');
  const [exchangeUserId, setExchangeUserId] = useState('');
  const [note, setNote] = useState('');
  const [lookupResult, setLookupResult] = useState<null | { username: string; status: string }>(null);
  const [lookupError, setLookupError] = useState('');
  const [looking, setLooking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleLookup() {
    if (!exchangeUserId.trim()) return;
    setLooking(true); setLookupError(''); setLookupResult(null);
    try {
      const u = await api.lookupExchangeUser(exchangeId, exchangeUserId.trim());
      setLookupResult({ username: u.username || u.userId, status: u.status });
    } catch {
      setLookupError('Không tìm thấy user này trong DB (chưa sync?)');
    } finally {
      setLooking(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!exchangeUserId.trim()) { setError('Nhập exchange user ID'); return; }
    setError(''); setSubmitting(true);
    try {
      await onLinked({ exchange_id: exchangeId, exchange_user_id: exchangeUserId.trim(), note });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Liên kết sàn giao dịch</h2>
          <button onClick={onClose}><X className="w-4 h-4 text-muted-foreground" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && <p className="text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">{error}</p>}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Sàn giao dịch</label>
            <select value={exchangeId} onChange={(e) => { setExchangeId(e.target.value); setLookupResult(null); setLookupError(''); }}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground">
              {exchanges.map((ex) => <option key={ex.id} value={ex.id}>{ex.name}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">
              UID trên sàn <span className="text-destructive">*</span>
            </label>
            <div className="flex gap-2 mt-1">
              <input
                value={exchangeUserId}
                onChange={(e) => { setExchangeUserId(e.target.value); setLookupResult(null); setLookupError(''); }}
                placeholder="Exchange user_id (vd: 37072419)"
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
              />
              <button type="button" onClick={handleLookup} disabled={looking || !exchangeUserId.trim()}
                className="flex items-center gap-1 px-3 py-2 bg-secondary rounded-lg text-xs text-muted-foreground hover:text-foreground disabled:opacity-50">
                {looking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Tra cứu'}
              </button>
            </div>
            {lookupResult && (
              <p className="mt-1.5 flex items-center gap-1 text-xs text-emerald-400">
                <Check className="w-3.5 h-3.5" /> Tìm thấy: <strong>{lookupResult.username}</strong> ({lookupResult.status})
              </p>
            )}
            {lookupError && <p className="mt-1.5 text-xs text-amber-400">{lookupError}</p>}
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Ghi chú (tuỳ chọn)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="vd: tài khoản chính"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground" />
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground bg-secondary rounded-lg">
              Huỷ
            </button>
            <button type="submit" disabled={submitting}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-60">
              {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Liên kết
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main detail page ──────────────────────────────────────────────────────────

export default function MemberDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const router = useRouter();

  const [member, setMember] = useState<CommunityMember | null>(null);
  const [stats, setStats] = useState<MemberStats | null>(null);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddLink, setShowAddLink] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // inline edit
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<MemberUpdatePayload>({});
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState('');

  useEffect(() => {
    Promise.all([
      api.getMember(id),
      api.getMemberStats(id),
      api.getExchanges(),
    ]).then(([m, s, ex]) => {
      setMember(m);
      setStats(s);
      setExchanges(ex);
      setEditForm({
        username: m.username,
        full_name: m.fullName,
        phone: m.phone,
        notes: m.notes,
        tags: m.tags,
        is_active: m.isActive,
      });
    }).finally(() => setLoading(false));
  }, [id]);

  async function handleSaveEdit() {
    setSaving(true); setEditError('');
    try {
      const updated = await api.updateMember(id, editForm);
      setMember(updated);
      setEditing(false);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Lỗi lưu');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm('Xoá member này?')) return;
    setDeleting(true);
    try {
      await api.deleteMember(id);
      router.push('/dashboard/members');
    } finally {
      setDeleting(false);
    }
  }

  async function handleAddLink(link: ExchangeLinkPayload) {
    const updated = await api.addExchangeLink(id, link);
    setMember(updated);
    const s = await api.getMemberStats(id);
    setStats(s);
    setShowAddLink(false);
  }

  async function handleRemoveLink(exchangeId: string, exchangeUserId: string) {
    if (!confirm('Gỡ liên kết này?')) return;
    await api.removeExchangeLink(id, exchangeId, exchangeUserId);
    const [updated, s] = await Promise.all([api.getMember(id), api.getMemberStats(id)]);
    setMember(updated);
    setStats(s);
  }

  if (loading) {
    return (
      <>
        <Header title="Member" subtitle="Loading..." />
        <div className="flex-1 p-6 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </>
    );
  }

  if (!member) {
    return (
      <>
        <Header title="Not found" subtitle="" />
        <div className="flex-1 p-6">
          <p className="text-muted-foreground">Không tìm thấy member.</p>
        </div>
      </>
    );
  }

  const exMap = Object.fromEntries(exchanges.map((e) => [e.id, e]));

  return (
    <>
      <Header
        title={member.username ? `@${member.username}` : member.fullName || member.platformId}
        subtitle={`${member.platform} · ${member.platformId}`}
      />
      <div className="flex-1 p-6 space-y-6">
        {/* Back */}
        <Link href="/dashboard/members"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-3.5 h-3.5" /> Tất cả members
        </Link>

        {/* Stats cards */}
        {stats && (
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Total Deposit', value: formatCurrency(stats.totalDeposit), Icon: Wallet, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
              { label: 'Trading Volume', value: formatCurrency(stats.totalVolume), Icon: TrendingUp, color: 'text-violet-400', bg: 'bg-violet-400/10' },
              { label: 'Commission', value: formatCurrency(stats.totalCommission), Icon: DollarSign, color: 'text-amber-400', bg: 'bg-amber-400/10' },
            ].map(({ label, value, Icon, color, bg }) => (
              <div key={label} className="bg-card border border-border rounded-xl p-5">
                <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>
                  <Icon className={`w-4 h-4 ${color}`} />
                </div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-xl font-bold text-foreground mt-0.5">{value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Info card */}
          <div className="bg-card border border-border rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Thông tin</h3>
              <div className="flex gap-2">
                {!editing ? (
                  <button onClick={() => setEditing(true)}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
                    <Pencil className="w-3.5 h-3.5" /> Sửa
                  </button>
                ) : (
                  <>
                    <button onClick={() => setEditing(false)}
                      className="text-xs text-muted-foreground hover:text-foreground">Huỷ</button>
                    <button onClick={handleSaveEdit} disabled={saving}
                      className="flex items-center gap-1 text-xs text-primary">
                      {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                      Lưu
                    </button>
                  </>
                )}
                <button onClick={handleDelete} disabled={deleting}
                  className="flex items-center gap-1.5 text-xs text-destructive hover:opacity-80">
                  {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                  Xoá
                </button>
              </div>
            </div>

            {editError && <p className="text-xs text-destructive">{editError}</p>}

            <div className="space-y-3 text-sm">
              {/* Platform */}
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs">Platform</span>
                <span className="flex items-center gap-1.5 text-sky-400 font-medium text-xs">
                  {member.platform === 'telegram' && <Send className="w-3.5 h-3.5" />}
                  {member.platform}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs">Platform ID</span>
                <span className="font-mono text-xs">{member.platformId}</span>
              </div>

              {/* Editable fields */}
              {([
                { label: 'Username',     formKey: 'username',  memberKey: 'username',  placeholder: '@username' },
                { label: 'Họ tên',       formKey: 'full_name', memberKey: 'fullName',  placeholder: 'Tên thật' },
                { label: 'Điện thoại',   formKey: 'phone',     memberKey: 'phone',     placeholder: '+84...' },
              ] as const).map(({ label, formKey, memberKey, placeholder }) => (
                <div key={formKey} className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground text-xs shrink-0">{label}</span>
                  {editing ? (
                    <input
                      value={(editForm[formKey] as string) ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, [formKey]: e.target.value }))}
                      placeholder={placeholder}
                      className="flex-1 text-right rounded border border-border bg-background px-2 py-1 text-xs text-foreground"
                    />
                  ) : (
                    <span className="text-foreground text-xs">{(member as any)[memberKey] || '—'}</span>
                  )}
                </div>
              ))}

              {/* Tags */}
              <div className="flex items-start justify-between gap-3">
                <span className="text-muted-foreground text-xs shrink-0 mt-1">Tags</span>
                {editing ? (
                  <div className="flex-1">
                    <input
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          const v = (e.target as HTMLInputElement).value.trim();
                          if (v && !editForm.tags?.includes(v)) {
                            setEditForm((f) => ({ ...f, tags: [...(f.tags ?? []), v] }));
                            (e.target as HTMLInputElement).value = '';
                          }
                        }
                      }}
                      placeholder="Nhập + Enter"
                      className="w-full text-right rounded border border-border bg-background px-2 py-1 text-xs text-foreground"
                    />
                    <div className="flex flex-wrap gap-1 mt-1 justify-end">
                      {(editForm.tags ?? []).map((t) => (
                        <span key={t} className="flex items-center gap-0.5 px-1.5 py-0.5 bg-primary/10 text-primary rounded text-xs">
                          {t}
                          <button onClick={() => setEditForm((f) => ({ ...f, tags: f.tags?.filter((x) => x !== t) }))}>
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-1 justify-end">
                    {member.tags.length > 0
                      ? member.tags.map((t) => (
                          <span key={t} className="px-1.5 py-0.5 bg-secondary text-muted-foreground rounded text-xs">{t}</span>
                        ))
                      : <span className="text-muted-foreground text-xs">—</span>}
                  </div>
                )}
              </div>

              {/* Notes */}
              <div className="flex items-start justify-between gap-3">
                <span className="text-muted-foreground text-xs shrink-0 mt-1">Ghi chú</span>
                {editing ? (
                  <textarea
                    value={editForm.notes ?? ''}
                    onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                    rows={2}
                    className="flex-1 text-right rounded border border-border bg-background px-2 py-1 text-xs text-foreground resize-none"
                  />
                ) : (
                  <span className="text-foreground text-xs text-right max-w-xs">{member.notes || '—'}</span>
                )}
              </div>

              {/* Active toggle */}
              {editing && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground text-xs">Active</span>
                  <button
                    type="button"
                    onClick={() => setEditForm((f) => ({ ...f, is_active: !f.is_active }))}
                    className={`w-10 h-5 rounded-full transition-colors ${editForm.is_active ? 'bg-emerald-500' : 'bg-secondary'}`}
                  >
                    <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${editForm.is_active ? 'translate-x-5' : ''}`} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Exchange links */}
          <div className="bg-card border border-border rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Link2 className="w-4 h-4 text-muted-foreground" />
                Sàn liên kết ({member.exchangeLinks.length})
              </h3>
              <button
                onClick={() => setShowAddLink(true)}
                className="flex items-center gap-1.5 text-xs text-primary hover:opacity-80"
              >
                <Plus className="w-3.5 h-3.5" /> Liên kết
              </button>
            </div>

            {member.exchangeLinks.length === 0 ? (
              <div className="py-8 flex flex-col items-center gap-2 text-muted-foreground">
                <Link2 className="w-8 h-8 opacity-30" />
                <p className="text-sm">Chưa liên kết sàn nào</p>
                <button
                  onClick={() => setShowAddLink(true)}
                  className="mt-1 text-xs text-primary hover:underline"
                >
                  Thêm liên kết đầu tiên
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {member.exchangeLinks.map((lnk) => {
                  const ex = exMap[lnk.exchangeId];
                  const stat = stats?.links.find(
                    (s) => s.exchangeId === lnk.exchangeId && s.exchangeUserId === lnk.exchangeUserId
                  );
                  return (
                    <div key={`${lnk.exchangeId}-${lnk.exchangeUserId}`}
                      className="rounded-lg border border-border p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {ex && (
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ex.color }} />
                          )}
                          <span className="text-sm font-medium text-foreground">
                            {ex?.name ?? lnk.exchangeId}
                          </span>
                          <span className="font-mono text-xs text-muted-foreground">
                            UID: {lnk.exchangeUserId}
                          </span>
                        </div>
                        <button
                          onClick={() => handleRemoveLink(lnk.exchangeId, lnk.exchangeUserId)}
                          className="text-muted-foreground hover:text-destructive transition-colors"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {stat && (
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <p className="text-muted-foreground">Deposit</p>
                            <p className="font-medium text-emerald-400">{formatCurrency(stat.totalDeposit)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Volume</p>
                            <p className="font-medium text-violet-400">{formatCurrency(stat.totalVolume)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Commission</p>
                            <p className="font-medium text-amber-400">{formatCurrency(stat.totalCommission)}</p>
                          </div>
                        </div>
                      )}

                      {lnk.note && (
                        <p className="text-xs text-muted-foreground italic">{lnk.note}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {showAddLink && (
        <AddLinkModal
          exchanges={exchanges}
          onClose={() => setShowAddLink(false)}
          onLinked={handleAddLink}
        />
      )}
    </>
  );
}
