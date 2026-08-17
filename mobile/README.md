# MwalimuKit — Mobile (Android)

Capacitor wrapper that packages the web PWA as a native Android app.
The web build (`web/`) remains the source of truth — this directory
contains only the native shell and build configuration.

## Prerequisites

- Node.js ≥ 20
- Android Studio (for building the APK/AAB)
- Android SDK (API 34+)

## Quick start

```bash
# From the monorepo root:
npm run android:sync   # build web + sync to Android
npm run android:open   # open in Android Studio
```

Or step by step:

```bash
cd ../web && npm run build   # build the PWA
cd ../mobile && npx cap sync android   # copy assets + update plugins
npx cap open android   # open Android Studio
```

## Building the APK

In Android Studio:
- **Debug**: Build → Build APK(s)
- **Release**: Build → Generate Signed Bundle / APK

Or via Gradle CLI:
```bash
cd android
./gradlew assembleDebug        # debug APK
./gradlew bundleRelease        # release AAB for Play Store
```

## Project structure

```
mobile/
├── capacitor.config.ts      Capacitor config (webDir → ../web/dist)
├── android/                  Native Android project
│   ├── app/src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── java/…/MainActivity.java
│   │   ├── res/               Icons, splash, colors, styles
│   │   └── assets/public/     Web build output (synced)
│   ├── build.gradle
│   └── variables.gradle
└── package.json
```

## Capacitor plugins

| Plugin | Purpose |
|--------|---------|
| `@capacitor/app` | Back button handling |
| `@capacitor/splash-screen` | Green splash on launch |
| `@capacitor/status-bar` | Green status bar |
| `@capacitor/haptics` | Tactile feedback on score taps |
| `@capacitor/keyboard` | Keyboard avoidance |

## App identity

- **Package**: `ke.mwalimukit.app`
- **Display name**: MwalimuKit
- **Min SDK**: 24 (Android 7.0)
- **Target SDK**: 36
