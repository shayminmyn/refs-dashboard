'use client';

import { useState, useEffect } from 'react';
import { api, Exchange } from '@/lib/api';

export function useExchanges() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getExchanges()
      .then(setExchanges)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { exchanges, loading, error };
}
