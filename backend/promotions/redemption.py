from decimal import Decimal, InvalidOperation

from config.platform_fees import (
    FAN_CREDIT_MAX_REDEEM_PER_PURCHASE,
    FAN_CREDIT_MAX_REDEEM_PER_TIP,
)

from .models import PromotionLedgerEntry
from .services import record_ledger_entry, wallet_balance

ZERO = Decimal("0.00")


def _decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def redeemable_for_transaction(user, transaction_amount, *, max_redeem=None):
    """How much discovery credit can apply to a tip or purchase."""
    if not getattr(user, "is_authenticated", False):
        return ZERO

    amount = _decimal(transaction_amount)
    if amount is None or amount <= ZERO:
        return ZERO

    balance = wallet_balance(user)
    if balance <= ZERO:
        return ZERO

    cap = _decimal(max_redeem) if max_redeem is not None else amount
    if cap is None:
        cap = amount

    return min(balance, amount, cap)


def redeem_discovery_credits(user, amount, *, description=""):
    """Debit fan wallet via REDEEM ledger entry."""
    redeem_amount = _decimal(amount)
    if redeem_amount is None or redeem_amount <= ZERO:
        return ZERO

    balance = wallet_balance(user)
    if redeem_amount > balance:
        return None

    record_ledger_entry(
        user,
        PromotionLedgerEntry.REDEEM,
        -redeem_amount,
        description=description[:255],
    )
    return redeem_amount


def redeem_for_tip(user, tip_amount, artist_label="", *, apply_credits=True):
    if not apply_credits:
        return ZERO, ""

    redeem_amount = redeemable_for_transaction(
        user,
        tip_amount,
        max_redeem=FAN_CREDIT_MAX_REDEEM_PER_TIP,
    )
    if redeem_amount <= ZERO:
        return ZERO, ""

    redeemed = redeem_discovery_credits(
        user,
        redeem_amount,
        description=f"Applied to tip for {artist_label or 'artist'}",
    )
    if redeemed is None:
        return None, "Not enough discovery credits."
    return redeemed, ""


def redeem_for_purchase(user, product_price, product_title="", *, apply_credits=True):
    if not apply_credits:
        return ZERO, ""

    redeem_amount = redeemable_for_transaction(
        user,
        product_price,
        max_redeem=FAN_CREDIT_MAX_REDEEM_PER_PURCHASE,
    )
    if redeem_amount <= ZERO:
        return ZERO, ""

    redeemed = redeem_discovery_credits(
        user,
        redeem_amount,
        description=f"Applied to purchase: {product_title or 'store item'}",
    )
    if redeemed is None:
        return None, "Not enough discovery credits."
    return redeemed, ""
