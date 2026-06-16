# Mobile And Native App Path

The app is now prepared as a basic installable web app with:

- `manifest.webmanifest`
- app icon
- theme metadata
- service worker shell cache
- responsive layout improvements

## Mobile web/PWA test checklist

Test these viewport widths:

- 390px iPhone
- 430px larger iPhone
- 360px Android
- 768px tablet

Manual checks:

- Signup/login forms fit without horizontal scrolling.
- Artist tabs scroll horizontally.
- Audio cards and product cards stack cleanly.
- Comment form stacks on narrow screens.
- File inputs are usable on iOS Safari and Android Chrome.
- Add-to-home-screen uses the correct name/icon.

## Native wrapper later

Once the web app is stable, use Capacitor:

```bash
cd frontend
npm install @capacitor/core @capacitor/cli
npx cap init INDIEFUND com.indiefund.app
npm run build
npx cap add ios
npx cap add android
npx cap sync
```

Native app work still needs:

- App Store / Play Store developer accounts
- native icons and splash assets
- push notification provider
- production HTTPS backend
- mobile privacy policy and terms
