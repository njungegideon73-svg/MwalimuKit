import { create } from 'zustand';

interface FeatureFlags {
  paywall_enabled: boolean;
  ai_generation_enabled: boolean;
  max_classes: number | null;
  max_learners_per_class: number | null;
}

interface FeatureFlagState extends FeatureFlags {
  loaded: boolean;
  setFlags: (flags: FeatureFlags) => void;
}

const defaults: FeatureFlags = {
  paywall_enabled: false,
  ai_generation_enabled: true,
  max_classes: null,
  max_learners_per_class: null,
};

export const useFeatureFlags = create<FeatureFlagState>((set) => ({
  ...defaults,
  loaded: false,

  setFlags: (flags) => set({ ...flags, loaded: true }),
}));
