"""
SSRF Protection — IP range checks, loopback prevention, and DNS resolution validation.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata (AWS/GCP/Azure)
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
]


def is_safe_url(url: str) -> tuple[bool, str]:
    """Check if URL targets a safe, public host (prevent SSRF)."""
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL structure: {e}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Blocked scheme '{parsed.scheme}'. Only http and https allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL."

    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal", "169.254.169.254"):
        return False, "Targeting loopback or metadata service host."

    # DNS check
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {e}"

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in BLOCKED_NETWORKS:
            if ip in network:
                return False, f"Resolved IP {ip_str} falls into prohibited network {network}"

    return True, ""
