import { CreditCard, ExternalLink } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';

interface Subscription {
  id: string | null;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
  plan: string;
  is_active: boolean;
}

export function BillingPage() {
  const { data: sub, isLoading } = useQuery<Subscription>({
    queryKey: ['billing-subscription'],
    queryFn: () => apiFetch('/billing/subscription'),
  });

  const checkoutMutation = useMutation({
    mutationFn: () => apiFetch<{ checkout_url: string }>('/billing/checkout', {
      method: 'POST',
      json: { price_id: 'price_mwalimukit_monthly' },
    }),
    onSuccess: (data) => {
      window.open(data.checkout_url, '_blank');
    },
    onError: () => toast.error('Stripe is not configured. Contact admin.'),
  });

  const portalMutation = useMutation({
    mutationFn: () => apiFetch<{ portal_url: string }>('/billing/portal', { method: 'POST' }),
    onSuccess: (data) => {
      window.open(data.portal_url, '_blank');
    },
    onError: () => toast.error('No active subscription to manage'),
  });

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="h-40 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  const isTrial = sub?.status === 'trialing';

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Subscription & Billing</h1>
        <p className="text-gray-500 text-sm mt-1">Manage your plan and billing</p>
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-10 w-10 rounded-lg bg-primary-50 flex items-center justify-center">
            <CreditCard className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">
              {isTrial ? 'Free Trial' : sub?.plan || 'No plan'}
            </h2>
            <p className="text-xs text-gray-500">
              Status: <span className="capitalize font-medium">{sub?.status ?? 'none'}</span>
            </p>
          </div>
        </div>

        {sub?.current_period_start && sub?.current_period_end && (
          <div className="text-sm text-gray-600 mb-3">
            <span className="text-gray-500">Current period: </span>
            {new Date(sub.current_period_start).toLocaleDateString()} — {new Date(sub.current_period_end).toLocaleDateString()}
          </div>
        )}

        {isTrial && sub?.current_period_end && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800 mb-4">
            Free trial ends {new Date(sub.current_period_end).toLocaleDateString()}. Upgrade to keep all features.
          </div>
        )}

        <div className="flex flex-wrap gap-3 mt-2">
          <button
            onClick={() => checkoutMutation.mutate()}
            disabled={checkoutMutation.isPending}
            className="btn-primary"
          >
            <ExternalLink className="h-4 w-4" />
            {checkoutMutation.isPending ? 'Redirecting...' : 'Upgrade'}
          </button>
          {!isTrial && sub?.id && (
            <button
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              className="btn-secondary"
            >
              <ExternalLink className="h-4 w-4" />
              {portalMutation.isPending ? 'Redirecting...' : 'Manage Subscription'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
