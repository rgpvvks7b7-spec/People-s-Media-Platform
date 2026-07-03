from collections import Counter

from django.contrib.auth import get_user_model

from .models import BetaFeedback

User = get_user_model()

CATEGORY_LABELS = dict(BetaFeedback.CATEGORIES)
SEVERITY_LABELS = dict(BetaFeedback.SEVERITIES)
SEVERITY_ORDER = [BetaFeedback.BLOCKER, BetaFeedback.HIGH, BetaFeedback.MEDIUM, BetaFeedback.LOW]
USER_TYPE_LABELS = dict(User.USER_TYPES)


def build_beta_feedback_report(limit_recent=12):
    queryset = BetaFeedback.objects.select_related("user").order_by("-created_at")
    total = queryset.count()

    by_category = Counter(queryset.values_list("category", flat=True))
    by_severity = Counter(queryset.values_list("severity", flat=True))
    by_user_type = Counter(queryset.values_list("user__user_type", flat=True))

    unresolved = queryset.filter(resolved=False)
    blockers = [
        {
            "id": item.id,
            "summary": item.summary,
            "category": item.category,
            "severity": item.severity,
            "path": item.path,
            "username": item.user.username,
            "user_type": item.user.user_type,
            "details": item.details,
        }
        for item in unresolved.filter(severity=BetaFeedback.BLOCKER)
    ]

    high_priority = [
        {
            "id": item.id,
            "summary": item.summary,
            "category": item.category,
            "severity": item.severity,
            "path": item.path,
            "username": item.user.username,
            "user_type": item.user.user_type,
        }
        for item in unresolved.filter(severity=BetaFeedback.HIGH)
    ]

    beta_testers = User.objects.filter(is_beta_tester=True).count()
    submitters = queryset.values("user_id").distinct().count()

    recent = [
        {
            "id": item.id,
            "summary": item.summary,
            "category": item.category,
            "severity": item.severity,
            "path": item.path,
            "username": item.user.username,
            "user_type": item.user.user_type,
            "resolved": item.resolved,
            "created_at": item.created_at,
        }
        for item in queryset[:limit_recent]
    ]

    return {
        "total_feedback": total,
        "beta_testers": beta_testers,
        "submitters": submitters,
        "participation_rate": round((submitters / beta_testers) * 100, 1) if beta_testers else 0.0,
        "unresolved_count": unresolved.count(),
        "by_category": {
            key: {
                "count": by_category.get(key, 0),
                "label": CATEGORY_LABELS.get(key, key),
            }
            for key, _ in BetaFeedback.CATEGORIES
        },
        "by_severity": {
            key: {
                "count": by_severity.get(key, 0),
                "label": SEVERITY_LABELS.get(key, key),
            }
            for key in SEVERITY_ORDER
        },
        "by_user_type": {
            key: {
                "count": by_user_type.get(key, 0),
                "label": USER_TYPE_LABELS.get(key, key),
            }
            for key, _ in User.USER_TYPES
        },
        "blockers": blockers,
        "high_priority": high_priority,
        "recent": recent,
    }


def format_beta_feedback_report(report):
    lines = [
        "",
        "=== IndieFund Beta Feedback Report ===",
        f"Total submissions: {report['total_feedback']}",
        f"Beta testers: {report['beta_testers']} | Submitted feedback: {report['submitters']} ({report['participation_rate']}%)",
        f"Unresolved: {report['unresolved_count']}",
        "",
        "By severity:",
    ]

    for key in SEVERITY_ORDER:
        row = report["by_severity"][key]
        lines.append(f"  {row['label']:8} {row['count']}")

    lines.append("")
    lines.append("By category:")
    for key, row in report["by_category"].items():
        if row["count"]:
            lines.append(f"  {row['label']:22} {row['count']}")

    lines.append("")
    lines.append("By account type:")
    for key, row in report["by_user_type"].items():
        if row["count"]:
            lines.append(f"  {row['label']:8} {row['count']}")

    if report["blockers"]:
        lines.append("")
        lines.append("Blockers (unresolved):")
        for item in report["blockers"]:
            lines.append(f"  [{item['username']}] {item['summary']}")
            if item["details"]:
                lines.append(f"    -> {item['details']}")

    if report["high_priority"]:
        lines.append("")
        lines.append("High priority (unresolved):")
        for item in report["high_priority"]:
            lines.append(f"  [{item['username']}] {item['summary']}")

    lines.append("")
    lines.append("Recent submissions:")
    for item in report["recent"]:
        status = "resolved" if item["resolved"] else item["severity"]
        lines.append(f"  [{item['username']}] ({status}) {item['summary']}")

    lines.append("")
    return "\n".join(lines)
