'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ReferredUser, UsersParams } from '@/lib/api';

interface UsersState {
  data: ReferredUser[];
  total: number;
  page: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
}

export function useUsers(initialParams: UsersParams) {
  const [params, setParams] = useState<UsersParams>(initialParams);
  const [state, setState] = useState<UsersState>({
    data: [],
    total: 0,
    page: 1,
    totalPages: 1,
    loading: true,
    error: null,
  });

  const fetchUsers = useCallback(async (p: UsersParams) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await api.getUsers(p);
      setState({
        data: res.data,
        total: res.pagination.total,
        page: res.pagination.page,
        totalPages: res.pagination.totalPages,
        loading: false,
        error: null,
      });
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to load users',
      }));
    }
  }, []);

  useEffect(() => {
    fetchUsers(params);
  }, [params, fetchUsers]);

  const updateParams = useCallback((updates: Partial<UsersParams>) => {
    setParams((prev) => ({ ...prev, ...updates }));
  }, []);

  return { ...state, params, updateParams, refetch: () => fetchUsers(params) };
}
