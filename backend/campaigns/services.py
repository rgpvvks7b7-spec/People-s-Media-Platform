from decimal import Decimal


def placeholder_metrics_for_campaign(campaign):
    """Deterministic placeholder analytics for launched campaigns."""
    if campaign.status != campaign.LAUNCHED:
        return {
            "impressions": 0,
            "clicks": 0,
            "follows": 0,
            "subscribers": 0,
            "purchases": 0,
            "revenue": Decimal("0.00"),
            "fan_value": Decimal("0.00"),
            "placeholder": False,
        }

    seed = campaign.id or 1
    daily = float(campaign.budget_daily or 10)
    duration = campaign.duration_days or 30
    factor = (seed % 7) + 3

    impressions = int(daily * duration * factor * 12)
    clicks = max(int(impressions * 0.018), 1)
    follows = max(int(clicks * 0.12), 0)
    subscribers = max(int(follows * 0.25), 0)
    purchases = max(int(clicks * 0.04), 0)
    revenue = Decimal(str(round(purchases * 4.5 + daily * 0.3, 2)))
    fan_value = Decimal(str(round(float(revenue) / max(subscribers + follows, 1), 2)))

    return {
        "impressions": impressions,
        "clicks": clicks,
        "follows": follows,
        "subscribers": subscribers,
        "purchases": purchases,
        "revenue": revenue,
        "fan_value": fan_value,
        "placeholder": True,
    }
