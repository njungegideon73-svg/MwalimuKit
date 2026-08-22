import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

interface Props {
  children: ReactNode;
  label?: string;
  fallback?: ReactNode;
}

/**
 * Wraps children in an ErrorBoundary with a route-specific label,
 * so a crash on one page doesn't take down the entire app.
 */
export class RouteErrorBoundary extends Component<Props> {
  render() {
    return (
      <ErrorBoundary label={this.props.label} onError={(err, info) => {
        if (import.meta.env.DEV) {
          console.error('[RouteErrorBoundary]', err, info.componentStack);
        }
      }}>
        {this.props.children}
      </ErrorBoundary>
    );
  }
}
