import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ke.mwalimukit.app',
  appName: 'MwalimuKit',
  webDir: '../web/dist',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: false,
      backgroundColor: '#0E7C66',
      showSpinner: true,
      spinnerColor: '#ffffff',
    },
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#0E7C66',
    },
  },
};

export default config;
