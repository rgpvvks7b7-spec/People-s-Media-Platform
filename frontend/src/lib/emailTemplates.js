/**
 * Build compliant plain-text email drafts for artists to copy into their own
 * mail client / ESP. IndieFund does not send these messages.
 */

const TEMPLATE_IDS = ["new_release", "local_show", "thank_you", "reengage"];

/**
 * @typedef {object} TemplateContext
 * @property {string} [stageName]
 * @property {string} [city]
 * @property {string} [publicUrl]
 * @property {string} [trackTitle]
 * @property {string} [venueName]
 * @property {string} [showDate]
 * @property {string} [ticketUrl]
 */

/**
 * @param {TemplateContext} context
 */
function complianceFooter(context) {
  const name = context.stageName || "this artist";
  return [
    "",
    "—",
    `You're receiving this because you opted in to share your email with ${name} on IndieFund.`,
    "Reply to unsubscribe, or revoke sharing anytime in your IndieFund Profile → Email preferences.",
  ].join("\n");
}

/**
 * @param {string} templateId
 * @param {TemplateContext} context
 */
export function buildEmailTemplate(templateId, context = {}) {
  const stageName = context.stageName || "Your artist";
  const publicUrl = context.publicUrl || "https://indiefund.app";
  const city = context.city || "";
  const footer = complianceFooter(context);

  if (templateId === "local_show") {
    const venue = context.venueName || "a local venue";
    const when = context.showDate || "soon";
    const ticket = context.ticketUrl || publicUrl;
    return {
      id: "local_show",
      label: "Upcoming local show",
      subject: `${stageName} live${city ? ` in ${city}` : ""} — ${when}`,
      body: [
        `Hey —`,
        "",
        `${stageName} is playing ${venue}${city ? ` in ${city}` : ""} (${when}).`,
        "",
        `Details / tickets: ${ticket}`,
        "",
        "Would love to see you there.",
        "",
        stageName,
        footer,
      ].join("\n"),
    };
  }

  if (templateId === "thank_you") {
    return {
      id: "thank_you",
      label: "Thank you",
      subject: `Thank you from ${stageName}`,
      body: [
        `Hey —`,
        "",
        `Just a quick thank you for supporting ${stageName}. Your support keeps the work going.`,
        "",
        `Catch up anytime: ${publicUrl}`,
        "",
        "Grateful,",
        stageName,
        footer,
      ].join("\n"),
    };
  }

  if (templateId === "reengage") {
    return {
      id: "reengage",
      label: "It's been a while",
      subject: `${stageName} — a quick update`,
      body: [
        `Hey —`,
        "",
        `It's been a little while. ${stageName} has new work and updates waiting for you.`,
        "",
        `Have a listen: ${publicUrl}`,
        "",
        "Hope to see you around,",
        stageName,
        footer,
      ].join("\n"),
    };
  }

  const track = context.trackTitle ? `“${context.trackTitle}”` : "a new release";
  return {
    id: "new_release",
    label: "New release / drop",
    subject: `${stageName} just shared ${track}`,
    body: [
      `Hey —`,
      "",
      `${stageName} just dropped ${track}.`,
      "",
      `Listen here: ${publicUrl}`,
      "",
      "Thanks for being on the list.",
      "",
      stageName,
      footer,
    ].join("\n"),
  };
}

export function listEmailTemplates() {
  return TEMPLATE_IDS.map(id => ({
    id,
    label: buildEmailTemplate(id).label,
  }));
}

export { TEMPLATE_IDS };
