export const CAMPAIGN_TYPE_DEFAULTS = {
  new_song: {
    goal: "more_streams",
    destination_type: "smart_link",
    titlePlaceholder: "e.g. Summer single push",
    audiencePlaceholder: "Indie pop fans who save new releases and follow similar artists on Spotify",
    creativeHeadlinePlaceholder: "New song out now",
    creativeTextPlaceholder: "Tap listen — we'd love to know what you think.",
  },
  album: {
    goal: "more_streams",
    destination_type: "smart_link",
    titlePlaceholder: "e.g. Album rollout — Project name",
    audiencePlaceholder: "Fans of your genre who listen to full projects, not just singles",
    creativeHeadlinePlaceholder: "The album is here",
    creativeTextPlaceholder: "Start with track one or jump to your favorite — links inside.",
  },
  artist_page: {
    goal: "new_followers",
    destination_type: "indiefund_page",
    titlePlaceholder: "e.g. Grow my artist profile",
    audiencePlaceholder: "People who follow new artists in your genre and city",
    creativeHeadlinePlaceholder: "New artist worth a follow",
    creativeTextPlaceholder: "Music, updates, and exclusive drops — all in one place.",
  },
  merch: {
    goal: "merch_sales",
    destination_type: "store",
    titlePlaceholder: "e.g. Tour tee drop",
    audiencePlaceholder: "Fans who buy band merch and support artists they discover online",
    creativeHeadlinePlaceholder: "New merch just dropped",
    creativeTextPlaceholder: "Limited run — grab yours before they're gone.",
  },
  show: {
    goal: "ticket_sales",
    destination_type: "external_url",
    titlePlaceholder: "e.g. Brooklyn show — March 15",
    audiencePlaceholder: "Live music fans in your show city and nearby towns",
    creativeHeadlinePlaceholder: "We're playing your city",
    creativeTextPlaceholder: "Tickets are live — come sing along with us.",
  },
  video: {
    goal: "video_views",
    destination_type: "streaming_link",
    titlePlaceholder: "e.g. Official video — Song title",
    audiencePlaceholder: "Fans who watch music videos and short clips on their phone",
    creativeHeadlinePlaceholder: "New video out now",
    creativeTextPlaceholder: "Watch the full visual and tell us your favorite moment.",
  },
};

export const CAMPAIGN_TYPE_TIPS = {
  new_song: {
    promote: "Single or release push — name the campaign after the track so you can compare results later.",
    goal: "Most artists start with more streams for a new song. You can always run a second campaign for followers or email signups.",
    networks: "Meta (Instagram and Facebook) is the most common starting point for song releases. Add TikTok if you have a strong short clip.",
    destination: "Send fans to a smart link with Spotify, Apple Music, and more — not straight to one app. That gives you one place to measure clicks.",
    audience: "Target fans of 2–3 similar artists in your lane, plus countries where your genre already travels well.",
    budget: "Many artists start around $10/day for 3–4 weeks. The first few days often look rough before things settle — that is normal.",
    creative: "Use a 15–30 second video with the hook: a lyric line, visualizer, or live moment. Lead with the part that stops the scroll.",
    review: "Double-check your smart link opens on mobile and that the right song is featured at the top.",
  },
  album: {
    promote: "Full project rollout — lead with your strongest track or a clear “start here” message on the landing page.",
    goal: "Streams are the usual first goal for an album. Email signups also work if you want to announce tour dates or merch later.",
    networks: "Meta plus YouTube often pair well for album campaigns — short clips for feeds, longer cuts for discovery.",
    destination: "One smart link for the whole project keeps reporting simple. Highlight your lead single there.",
    audience: "Broader genre targeting works here — think fans of several artists in your world, not just one narrow niche.",
    budget: "Album campaigns often run 4–6 weeks. Consider $12–15/day if your budget allows a longer learning period.",
    creative: "Test different hooks from different songs. Even small changes in the opening seconds can shift results.",
    review: "Make sure every streaming button on your landing page works before you mark this ready.",
  },
  artist_page: {
    promote: "Grow your overall profile — you are introducing the artist, not just one release.",
    goal: "New followers or email signups are the clearest wins when the goal is long-term profile growth.",
    networks: "Instagram and TikTok usually outperform for discovery-style profile ads. Meta is still a solid default.",
    destination: "Your IndieFund page or link-in-bio hub works best — give fans several ways to follow, listen, and subscribe.",
    audience: "Target by genre and vibe, not just one song. Describe the kind of fan who would stick around after one visit.",
    budget: "Profile growth is a marathon — steady $8–10/day over a month often beats one short expensive burst.",
    creative: "Show your face, studio, or live energy. Let people feel who you are in the first three seconds.",
    review: "Open your destination link as if you are a new fan — is it obvious how to follow and listen?",
  },
  merch: {
    promote: "Promote a store item — feature one product with a clear photo and price in mind.",
    goal: "Merch sales is the natural goal. Pair it with creative that shows the product clearly.",
    networks: "Meta is the usual starting point. Pinterest can help for visual products like prints, apparel, or pins.",
    destination: "Link directly to your store page or IndieFund shop listing so buyers land on the exact item.",
    audience: "Target fans of similar artists who buy band merch. Add your show cities if the item ties to a tour.",
    budget: "Shorter bursts often work — try $10/day for about two weeks around a drop or restock.",
    creative: "Clean product shots or someone wearing the merch usually outperform plain artwork alone.",
    review: "Confirm the link opens the correct product and that checkout works on mobile.",
  },
  show: {
    promote: "Sell tickets or RSVPs — put the date, city, and venue in the campaign name.",
    goal: "Ticket sales or RSVP signups — pick the goal that matches how you are actually selling the show.",
    networks: "Meta with location targeting around the venue city is key. TikTok can help for younger rooms.",
    destination: "Use your ticket link or RSVP page. The next step should be obvious — no extra clicks if you can avoid them.",
    audience: "Focus on the show city and nearby towns. Location matters more than genre for local gigs.",
    budget: "Start 2–3 weeks before the show. Many artists increase spend in the final week if tickets are moving slowly.",
    creative: "Crowd energy, venue shots, or a quick “we are playing [city] on [date]” clip usually convert well.",
    review: "Check the date, city, and ticket link one more time — typos here cost real sales.",
  },
  video: {
    promote: "Music video or clip — name the campaign after the video title so you can track what resonates.",
    goal: "Video views is the natural fit. You can also drive streams if the landing page links to your music.",
    networks: "YouTube and TikTok are naturals for video. Meta works well with a tight 10–20 second cut.",
    destination: "YouTube watch page, smart link under the video, or both — avoid sending people to a dead end.",
    audience: "Similar artists plus genre fans who watch music videos on their phone.",
    budget: "Video ads often need a week to find the right viewers. Give it time before you change too much.",
    creative: "Use the most engaging 10–20 seconds — not the full video. Hook first, then invite them to watch more.",
    review: "Preview your clip with sound off and with sound on — both matter on social feeds.",
  },
};

export function getCampaignTypeMeta(campaignType) {
  return CAMPAIGN_TYPES.find(item => item.id === campaignType) || CAMPAIGN_TYPES[0];
}

export const CAMPAIGN_TYPES = [
  { id: "new_song", label: "New song", detail: "Single or release push" },
  { id: "album", label: "Album", detail: "Full project rollout" },
  { id: "artist_page", label: "Artist page", detail: "Grow your overall profile" },
  { id: "merch", label: "Merch", detail: "Promote a store item" },
  { id: "show", label: "Show", detail: "Sell tickets or RSVPs" },
  { id: "video", label: "Video", detail: "Music video or clip" },
];

export function getStepTip(campaignType, stepId) {
  return CAMPAIGN_TYPE_TIPS[campaignType]?.[stepId] || CAMPAIGN_TYPE_TIPS.new_song[stepId] || "";
}

export function getCampaignDefaults(campaignType, artistPageUrl = "") {
  const defaults = CAMPAIGN_TYPE_DEFAULTS[campaignType] || CAMPAIGN_TYPE_DEFAULTS.new_song;
  return {
    ...defaults,
    destination_url: campaignType === "artist_page" ? artistPageUrl : "",
  };
}
