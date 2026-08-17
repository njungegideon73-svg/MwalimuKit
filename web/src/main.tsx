import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import App from './app/App';
import './styles/globals.css';

async function bootstrap() {
  // Capacitor-specific: hide splash screen when app is ready
  try {
    const { SplashScreen } = await import('@capacitor/splash-screen');
    await SplashScreen.hide();
  } catch {
    // Not running in Capacitor — skip
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <BrowserRouter>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: { fontSize: '14px', maxWidth: '400px' },
            success: { iconTheme: { primary: '#0E7C66', secondary: '#fff' } },
            error: { iconTheme: { primary: '#dc2626', secondary: '#fff' } },
          }}
        />
      </BrowserRouter>
    </StrictMode>,
  );
}

bootstrap();
