import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@mwalimukit/types': path.resolve(__dirname, '../packages/shared/types/src'),
      '@mwalimukit/curriculum': path.resolve(__dirname, '../packages/shared/curriculum'),
      '@mwalimukit/rubrics': path.resolve(__dirname, '../packages/shared/rubrics/src'),
    },
  },
});
