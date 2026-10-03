"""
Field Normalizers — clean URLs, dates, currencies (global + Indian), phone numbers, and whitespace.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = frozenset([
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid", "msclkid",
])


def normalize_whitespace(text: str) -> str:
    """Trim and collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(url: str) -> str:
    """Canonicalize URL: lowercase host, strip tracking params, strip trailing slash."""
    if not url:
        return ""
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        clean_netloc = parsed.netloc.lower()
        if clean_netloc.startswith("www."):
            clean_netloc = clean_netloc[4:]

        # Filter out tracking query params
        qs = parse_qs(parsed.query, keep_blank_values=False)
        cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in TRACKING_PARAMS}
        clean_query = urlencode(cleaned_qs, doseq=True)

        clean_path = parsed.path.rstrip("/")
        if not clean_path and not clean_query:
            clean_path = ""

        canonical = urlunparse((
            parsed.scheme.lower(),
            clean_netloc,
            clean_path,
            parsed.params,
            clean_query,
            "",  # strip fragment
        ))
        return canonical
    except Exception:
        return url


def parse_currency(text: str) -> Optional[tuple[float, str]]:
    """
    Parse currency strings:
    '$2.5M', '₹41 Cr', '€500K', '$1.2B', 'Rs 50 Lakh', '100 Million USD'
    Indian units: Cr -> 1e7, Lakh -> 1e5. Global: M -> 1e6, B -> 1e9, K -> 1e3.
    """
    if not text:
        return None
    raw = str(text).strip()

    # Detect currency code
    code = "USD"
    if "₹" in raw or "rs" in raw.lower() or "inr" in raw.lower():
        code = "INR"
    elif "€" in raw or "eur" in raw.lower():
        code = "EUR"
    elif "£" in raw or "gbp" in raw.lower():
        code = "GBP"

    # Multipliers
    multiplier = 1.0
    upper = raw.upper()

    if "CR" in upper or "CRORE" in upper:
        multiplier = 1e7
    elif "LAKH" in upper or "LAC" in upper:
        multiplier = 1e5
    elif "B" in upper or "BILLION" in upper:
        multiplier = 1e9
    elif "M" in upper or "MILLION" in upper:
        multiplier = 1e6
    elif "K" in upper or "THOUSAND" in upper:
        multiplier = 1e3

    # Extract digits
    match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not match:
        return None

    try:
        base_num = float(match.group(1))
        total_amount = base_num * multiplier
        return total_amount, code
    except ValueError:
        return None


def normalize_date(text: str) -> Optional[str]:
    """Parse various date formats, return ISO-8601 YYYY-MM-DD or None."""
    if not text:
        return None
    cleaned = str(text).strip()

    # Handle range e.g. "March 15-17, 2026" -> "March 15, 2026"
    range_match = re.search(r"([A-Za-z]+)\s+(\d+)\s*[-–]\s*\d+,\s*(\d{4})", cleaned)
    if range_match:
        cleaned = f"{range_match.group(1)} {range_match.group(2)}, {range_match.group(3)}"

    formats = [
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try year only e.g. "2024"
    if re.fullmatch(r"\d{4}", cleaned):
        return f"{cleaned}-01-01"

    return None


def normalize_phone(text: str) -> Optional[str]:
    """Normalize phone numbers to standard format."""
    if not text:
        return None
    digits = re.sub(r"[^\d+]", "", str(text))
    if len(digits) >= 10:
        return digits
    return None


def apply_normalizers(value: Any, field_type: str) -> Any:
    """Apply type-appropriate normalizer to extracted value."""
    if value is None:
        return None

    str_val = str(value)
    if field_type == "url":
        return normalize_url(str_val)
    elif field_type == "string":
        return normalize_whitespace(str_val)
    elif field_type == "currency":
        parsed = parse_currency(str_val)
        if parsed:
            amt, code = parsed
            if amt >= 1e7 and code == "INR":
                return f"₹{amt/1e7:.1f} Cr"
            elif amt >= 1e6:
                return f"${amt/1e6:.1f}M" if code == "USD" else f"{amt/1e6:.1f}M {code}"
            elif amt >= 1e3:
                return f"${amt/1e3:.0f}K" if code == "USD" else f"{amt/1e3:.0f}K {code}"
            return f"{amt:.2f} {code}"
        return normalize_whitespace(str_val)
    elif field_type == "date":
        norm_d = normalize_date(str_val)
        return norm_d if norm_d else normalize_whitespace(str_val)
    elif field_type == "phone":
        norm_p = normalize_phone(str_val)
        return norm_p if norm_p else normalize_whitespace(str_val)

    return value
