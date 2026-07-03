from accounts.email_verification import verification_required


def billing_allowed(user):
    if not user.is_authenticated:
        return False, "Authentication required"
    if verification_required(user):
        return False, "Verify your email before making purchases or receiving payouts."
    return True, ""
