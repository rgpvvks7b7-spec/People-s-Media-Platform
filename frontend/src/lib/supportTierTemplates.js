export const SUPPORT_TIER_TEMPLATES = [
  {
    id: "supporter",
    label: "$1 Supporter",
    name: "Supporter",
    monthly_amount: "1.00",
    benefits: "Early updates, ticket presales, and listening-party invites.",
  },
  {
    id: "member",
    label: "$5 Member",
    name: "Member",
    monthly_amount: "5.00",
    benefits: "Supporter-only drops, demos, process posts, and early access windows.",
  },
];

/**
 * Templates the artist has not yet created for the given profession.
 * Matching is by tier name (case-insensitive) so one-click stays idempotent.
 */
export function availableSupportTierTemplates(existingTiers = [], profession = "") {
  const usedNames = new Set(
    (existingTiers || [])
      .filter(tier => !profession || tier.profession === profession)
      .map(tier => String(tier.name || "").trim().toLowerCase())
  );
  return SUPPORT_TIER_TEMPLATES.filter(template => !usedNames.has(template.name.toLowerCase()));
}
