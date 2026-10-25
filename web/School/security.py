from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.utils.crypto import constant_time_compare


def is_hashed(stored):
    """True if the stored value is already a Django password hash."""
    try:
        identify_hasher(stored)
        return True
    except ValueError:
        return False


def verify_password(typed, stored):
    """Check a typed password against the stored one.

    Returns (ok, new_hash). new_hash is not None when an old plain-text
    password matched: the caller should save it so the account is upgraded.
    """
    if not stored:
        return False, None
    stored = str(stored)
    if is_hashed(stored):
        return check_password(typed, stored), None
    if constant_time_compare(typed, stored):  # old plain-text account
        return True, make_password(typed)
    return False, None


def login_session(request, role, user_id, **extra):
    """Start a fresh session for a logged-in user."""
    request.session.flush()  # new session id, old data removed
    request.session["role"] = role
    request.session["user_id"] = int(user_id)
    for key, value in extra.items():
        request.session[key] = value
