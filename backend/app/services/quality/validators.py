"""
Field Validators — url, email, phone, regex, min_len, max_len, range, enum.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

ValidatorResult = tuple[bool, Optional[Any], Optional[str]]  # (ok, fixed_value, failure_reason)


def validate_url(value: Any) -> ValidatorResult:
    if value is None:
        return True, None, None
    s = str(value).strip()
    if " " in s:
        return False, None, "URL cannot contain spaces"
    if not (s.startswith("http://") or s.startswith("https://")):
        s = "https://" + s
    try:
        p = urlparse(s)
        if p.scheme in ("http", "https") and p.netloc and ("." in p.netloc or p.netloc == "localhost"):
            return True, s, None
    except Exception:
        pass
    return False, None, "Invalid URL structure"


def validate_email(value: Any) -> ValidatorResult:
    if value is None:
        return True, None, None
    s = str(value).strip()
    if re.fullmatch(r"[^@]+@[^@]+\.[^@]+", s):
        return True, s.lower(), None
    return False, None, "Invalid email format"


def validate_phone(value: Any) -> ValidatorResult:
    if value is None:
        return True, None, None
    digits = re.sub(r"[^\d+]", "", str(value))
    if len(digits) >= 8:
        return True, digits, None
    return False, None, "Phone number has fewer than 8 digits"


def validate_regex(value: Any, pattern: str) -> ValidatorResult:
    if value is None:
        return True, None, None
    s = str(value)
    if re.search(pattern, s):
        return True, s, None
    return False, None, f"Value did not match pattern '{pattern}'"


def validate_min_len(value: Any, min_len: int) -> ValidatorResult:
    if value is None:
        return True, None, None
    s = str(value)
    if len(s) >= min_len:
        return True, s, None
    return False, None, f"Length {len(s)} is less than required minimum {min_len}"


def validate_max_len(value: Any, max_len: int) -> ValidatorResult:
    if value is None:
        return True, None, None
    s = str(value)
    if len(s) <= max_len:
        return True, s, None
    return False, None, f"Length {len(s)} exceeds maximum {max_len}"


def validate_range(value: Any, min_val: float, max_val: float) -> ValidatorResult:
    if value is None:
        return True, None, None
    try:
        n = float(re.sub(r"[^\d.-]", "", str(value)))
        if min_val <= n <= max_val:
            return True, n, None
        return False, None, f"Value {n} outside bounds [{min_val}, {max_val}]"
    except ValueError:
        return False, None, "Could not parse numeric value for range check"


def validate_enum(value: Any, allowed: list[str]) -> ValidatorResult:
    if value is None:
        return True, None, None
    s = str(value).strip()
    for option in allowed:
        if s.lower() == option.strip().lower():
            return True, option.strip(), None
    return False, None, f"Value '{s}' not in permitted choices: {allowed}"


def run_validators(value: Any, validator_specs: list[str]) -> ValidatorResult:
    """Run all specified validators sequentially. First error stops validation."""
    current_val = value
    for spec in validator_specs:
        if not spec:
            continue
        spec = spec.strip()

        if spec == "url":
            ok, fixed, reason = validate_url(current_val)
        elif spec == "email":
            ok, fixed, reason = validate_email(current_val)
        elif spec == "phone":
            ok, fixed, reason = validate_phone(current_val)
        elif spec.startswith("regex:"):
            ok, fixed, reason = validate_regex(current_val, spec[6:])
        elif spec.startswith("min_len:"):
            try:
                ok, fixed, reason = validate_min_len(current_val, int(spec[8:]))
            except ValueError:
                continue
        elif spec.startswith("max_len:"):
            try:
                ok, fixed, reason = validate_max_len(current_val, int(spec[8:]))
            except ValueError:
                continue
        elif spec.startswith("range:"):
            parts = spec[6:].split(",")
            try:
                ok, fixed, reason = validate_range(current_val, float(parts[0]), float(parts[1]))
            except (ValueError, IndexError):
                continue
        elif spec.startswith("enum:"):
            choices = [c.strip() for c in spec[5:].split(",")]
            ok, fixed, reason = validate_enum(current_val, choices)
        else:
            continue

        if not ok:
            return False, None, reason
        if fixed is not None:
            current_val = fixed

    return True, current_val, None
