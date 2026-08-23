import { Component, type ErrorInfo, type ReactNode } from 'react';
import Sentry from '@/lib/sentry';

interface Props {
  children: ReactNode;
  /** Optional label shown in the fallback UI. */
  label?: string;
  /** Callback invoked with the error + stack for external reporting. */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface State {
  error: Error | null;
}

/**
 * Top-level crash guard: renders a friendly fallback instead of a blank
 * screen when an unhandled render/error-boundary error escapes.
 * Reports errors to Sentry (if initialized) and to a provided callback.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary] Unhandled UI error:', error, info.componentStack);
    Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
    this.props.onError?.(error, info);
  }

  private handleReload = () => {
    window.location.href = '/';
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const label = this.props.label || 'Something went wrong';

    return (
      <div
        role="alert"
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
          padding: '2rem',
          textAlign: 'center',
        }}
      >
        <h1>{label}</h1>
        <p style={{ maxWidth: '32rem' }}>
          An unexpected error occurred. Your data is saved locally — please reload the app.
          If the problem persists, log in again.
        </p>
        {import.meta.env.DEV && (
          <pre style={{ maxWidth: '48rem', overflow: 'auto', fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
            {error.message}
            {'\n\n'}
            {this.state.error?.stack}
          </pre>
        )}
        <button type="button" onClick={this.handleReload} style={{ padding: '0.5rem 1.25rem' }}>
          Reload app
        </button>
      </div>
    );
  }
}
