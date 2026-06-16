# Product Blueprint

## User routes
### Artist onboarding
1. Create account as artist
2. Choose stage name, genre, city, influences
3. Upload profile/hero images
4. Create first post/music upload/product
5. Invite existing fans

### Fan onboarding
1. Create account as fan
2. Pick favourite genres/artists/sounds
3. See discovery feed
4. Subscribe to first artist for $1 or custom amount
5. Track subscription count out of 50

## Subscription rules
- Default minimum: $1/month per artist
- Fan default artist limit: 50
- At 50 active subscriptions, prompt: “Want to extend your artist discovery limit?”
- Future payment provider: Stripe

## Discovery algorithm direction
Recommendation score = similarity + uniqueness + engagement quality - spam/viral-chasing penalty.

Inputs:
- genres liked
- artists subscribed to
- music listened to
- saves/comments
- skipped artists
- artist uniqueness tags

Goal:
- Avoid TikTok-style viral-only feed
- Avoid YouTube-style same-loop trap
- Show familiar style with fresh flavour
