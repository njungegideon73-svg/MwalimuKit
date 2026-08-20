# MwalimuKit — Mobile (Android)

Capacitor wrapper that packages the web PWA as a native Android app.
The web build (`web/`) remains the source of truth — this directory
contains only the native shell and build configuration.

## Prerequisites

- Node.js ≥ 20
- Android Studio (for building the APK/AAB)
- Android SDK (API 34+)

## Quick start

The root scripts ensure the web app is built before syncing to Android:

```bash
# From the monorepo root — both scripts build web first, then sync to Android:
npm run android:sync   # build web + cap sync android
npm run android:open   # build web + cap open android
```

You can also run each step manually:

```bash
npm --workspace web run build     # build the PWA into web/dist
npm --workspace mobile run sync   # copy assets + update plugins
npm --workspace mobile run open   # open Android Studio
```

> **Note:** `android:open` used to skip the web build. It now builds web first so
> the Capacitor native shell always has a fresh `web/dist` to serve.

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
