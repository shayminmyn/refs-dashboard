'use client';

import { useState } from 'react';
import { Search, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { ReferredUser, UsersParams } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

interface UsersTableProps {
  users: ReferredUser[];
  total: number;
  page: number;
  totalPages: number;
  loading?: boolean;
  onParamsChange: (params: Partial<UsersParams>) => void;
  currentParams: UsersParams;
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-400/10 text-emerald-400',
  inactive: 'bg-muted text-muted-foreground',
};

export default function UsersTable({
  users,
  total,
  page,
  totalPages,
  loading,
  onParamsChange,
  currentParams,
}: UsersTableProps) {
  const [searchInput, setSearchInput] = useState(currentParams.search ?? '');

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    onParamsChange({ search: searchInput, page: '1' });
  }

  function handleSort(field: string) {
    const isCurrentField = currentParams.sortBy === field;
    onParamsChange({
      sortBy: field,
      sortDir: isCurrentField && currentParams.sortDir === 'desc' ? 'asc' : 'desc',
    });
  }

  const columns = [
    { key: 'userId', label: 'User ID' },
    { key: 'username', label: 'Username' },
    { key: 'registeredAt', label: 'Registered' },
    { key: 'totalDeposit', label: 'Deposit' },
    { key: 'totalVolume', label: 'Volume' },
    { key: 'totalCommission', label: 'Commission' },
    { key: 'status', label: 'Status' },
  ];

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {/* Table toolbar */}
      <div className="p-4 border-b border-border flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 min-w-48">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search users..."
              className="w-full pl-9 pr-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
          >
            Search
          </button>
        </form>

        {/* Status filter */}
        <select
          value={currentParams.status ?? ''}
          onChange={(e) => onParamsChange({ status: e.target.value, page: '1' })}
          className="px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <span className="text-sm text-muted-foreground ml-auto">
          {total} users
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider cursor-pointer hover:text-foreground transition select-none"
                  onClick={() => handleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      <div className="h-4 bg-secondary animate-pulse rounded" />
                    </td>
                  ))}
                </tr>
              ))
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground">
                  No users found
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user._id} className="hover:bg-accent/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{user.userId}</td>
                  <td className="px-4 py-3 font-medium text-foreground">{user.username || '—'}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {user.registeredAt ? formatDate(user.registeredAt) : '—'}
                  </td>
                  <td className="px-4 py-3 text-foreground">{formatCurrency(user.totalDeposit)}</td>
                  <td className="px-4 py-3 text-foreground">{formatCurrency(user.totalVolume)}</td>
                  <td className="px-4 py-3 font-semibold text-amber-400">
                    {formatCurrency(user.totalCommission)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[user.status]}`}>
                      {user.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-border flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-1">
            <button
              disabled={page <= 1}
              onClick={() => onParamsChange({ page: String(page - 1) })}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => onParamsChange({ page: String(page + 1) })}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
