import { Settings, Save } from 'lucide-react';
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';

interface FeatureFlags {
  paywall_enabled: boolean;
  ai_generation_enabled: boolean;
  max_classes: number | null;
  max_learners_per_class: number | null;
}

export function SystemSettingsPage() {
  const [flags, setFlags] = useState<FeatureFlags>({
    paywall_enabled: false,
    ai_generation_enabled: true,
    max_classes: null,
    max_learners_per_class: null,
  });

  const updateMutation = useMutation({
    mutationFn: (data: { key: string; value: boolean | number | null }) =>
      apiFetch('/super-admin/settings', { method: 'PATCH', json: data }),
    onSuccess: () => {
      alert('Settings updated successfully');
    },
  });

  const handleSave = () => {
    Object.entries(flags).forEach(([key, value]) => {
      updateMutation.mutate({ key, value });
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-gray-50 flex items-center justify-center">
          <Settings className="h-5 w-5 text-gray-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
          <p className="text-sm text-gray-500">Configure system-wide feature flags and settings</p>
        </div>
      </div>

      <div className="card space-y-6">
        <h2 className="font-semibold text-gray-900">Feature Flags</h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border border-gray-100">
            <div>
              <p className="font-medium text-gray-900">Paywall Enabled</p>
              <p className="text-sm text-gray-500">Enable payment requirements for premium features</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={flags.paywall_enabled}
                onChange={(e) => setFlags({ ...flags, paywall_enabled: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg border border-gray-100">
            <div>
              <p className="font-medium text-gray-900">AI Generation Enabled</p>
              <p className="text-sm text-gray-500">Allow AI-powered assessment generation</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={flags.ai_generation_enabled}
                onChange={(e) => setFlags({ ...flags, ai_generation_enabled: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
            </label>
          </div>

          <div className="p-4 rounded-lg border border-gray-100">
            <div className="mb-2">
              <p className="font-medium text-gray-900">Max Classes per Teacher</p>
              <p className="text-sm text-gray-500">Maximum number of classes a teacher can create (null = unlimited)</p>
            </div>
            <input
              type="number"
              value={flags.max_classes ?? ''}
              onChange={(e) => setFlags({ ...flags, max_classes: e.target.value ? parseInt(e.target.value) : null })}
              className="input w-full sm:w-48"
              placeholder="Unlimited"
              min="1"
            />
          </div>

          <div className="p-4 rounded-lg border border-gray-100">
            <div className="mb-2">
              <p className="font-medium text-gray-900">Max Learners per Class</p>
              <p className="text-sm text-gray-500">Maximum number of learners per class (null = unlimited)</p>
            </div>
            <input
              type="number"
              value={flags.max_learners_per_class ?? ''}
              onChange={(e) => setFlags({ ...flags, max_learners_per_class: e.target.value ? parseInt(e.target.value) : null })}
              className="input w-full sm:w-48"
              placeholder="Unlimited"
              min="1"
            />
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            <Save className="h-4 w-4" />
            {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">System Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-gray-50">
            <p className="text-sm text-gray-500">System Version</p>
            <p className="text-lg font-semibold text-gray-900">v0.1.0</p>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <p className="text-sm text-gray-500">Environment</p>
            <p className="text-lg font-semibold text-gray-900">Production</p>
          </div>
        </div>
      </div>
    </div>
  );
}
