# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Prompt injection sanitizer + SSRF protection for LLM applications.

Blocks 30+ injection patterns (English, Chinese, Japanese), strips invisible
Unicode characters, and validates URLs against SSRF via DNS resolution.

Usage:
    from sanitizer import sanitize_external_content, is_safe_url

    clean = sanitize_external_content(untrusted_text)
    if is_safe_url(user_provided_url):
        fetch(user_provided_url)
"""

__all__ = ['sanitize_external_content', 'is_safe_url', 'INJECTION_PATTERNS']
__version__ = '1.0.0'

import ipaddress
import logging
import re
import socket
import unicodedata
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    # Direct instruction override
    r'(?i)ignore\s+(all\s+)?previous\s+instructions',
    r'(?i)forget\s+(all\s+)?(your|previous)\s+(instructions|rules|context)',
    r'(?i)disregard\s+(all\s+)?(your|previous|above)',
    r'(?i)do\s+not\s+follow\s+(your|the)\s+(system|original)',
    r'(?i)override\s+(system|instructions|rules|prompt)',
    r'(?i)new\s+instructions?\s*:',
    r'(?i)your\s+new\s+(role|task|instructions?)\s+(is|are)',
    # Role hijacking
    r'(?i)you\s+are\s+now\s+a',
    r'(?i)act\s+as\s+(if\s+you\s+are|a)',
    r'(?i)pretend\s+(you\s+are|to\s+be)',
    r'(?i)switch\s+to\s+.{0,20}\s+mode',
    # Prompt leaking
    r'(?i)system\s*prompt\s*:',
    r'(?i)show\s+me\s+your\s+(system|instructions|prompt)',
    r'(?i)repeat\s+(your|the)\s+(system|instructions|prompt)',
    r'(?i)what\s+are\s+your\s+(instructions|rules)',
    # Fake conversation markers
    r'(?i)<\s*system\s*>.*?<\s*/\s*system\s*>',
    r'(?i)\[INST\].*?\[/INST\]',
    r'(?i)###\s*(System|Human|Assistant)\s*:',
    r'(?i)assistant\s*:\s*certainly',
    r'(?i)human\s*:\s*',
    # Dangerous commands
    r'(?i)execute\s+(this|the\s+following)\s+command',
    r'(?i)run\s+(this|the\s+following)\s+(bash|shell|command)',
    r'(?i)write\s+to\s+(file|disk|path)',
    r'(?i)delete\s+(all|the|every)\s+files?',
    r'(?i)rm\s+-rf\s+/',
    r'(?i)curl\s+.*?\|\s*(?:ba)?sh',
    r'(?i)wget\s+.*?&&\s*(?:ba)?sh',
    # Exfiltration attempts
    r'(?i)send\s+(the|your|all)\s+(api|secret|token|key|env|password)',
    r'(?i)exfiltrate',
    r'(?i)post\s+.*?(api[_-]?key|token|secret|password)',
    # Chinese injection phrases
    r'忽略之前的指令',
    r'忽略前面的指示',
    r'忽略以上指令',
    r'你现在是',
    r'你現在是',
    r'假装你是',
    # Japanese injection phrases
    r'以前の指示を無視',
    r'あなたは今',
]

_COMPILED = [re.compile(p) for p in INJECTION_PATTERNS]

# Zero-width / invisible characters to strip
_ZERO_WIDTH = re.compile('[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u2061\u2062\u2063\u2064\u00ad]')


def sanitize_external_content(text: str) -> str:
    """Strip prompt injection patterns from external content.

    Returns the text with injection attempts replaced by [BLOCKED].
    Safe to call on any external content before feeding to LLM.
    """
    # Unicode NFKC normalization (collapses lookalike chars before matching)
    text = unicodedata.normalize('NFKC', text)
    # Strip zero-width / invisible characters
    text = _ZERO_WIDTH.sub('', text)
    for pattern in _COMPILED:
        text = pattern.sub('[BLOCKED]', text)
    return text


# ── SSRF protection ─────────────────────────────────────────────────

_PRIVATE_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('0.0.0.0/8'),
]


_BLOCKED_HOSTNAMES = {'localhost', '0.0.0.0', ''}


def _is_private_or_loopback(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is private, loopback, link-local, or otherwise unsafe."""
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_reserved
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
    )


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch (blocks private IPs, localhost, file://).

    Performs actual DNS resolution to catch SSRF bypasses via hex IPs,
    decimal IPs, IPv6-mapped IPv4, short forms, etc.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Block non-HTTP(S) schemes
    if parsed.scheme not in ('http', 'https'):
        return False

    hostname = (parsed.hostname or '').lower()

    # Block known unsafe hostnames
    if hostname in _BLOCKED_HOSTNAMES:
        return False

    # Check if hostname is a raw IP (v4 or v6, any encoding)
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_private_or_loopback(addr):
            return False
        # Also check IPv6-mapped IPv4 (e.g. ::ffff:127.0.0.1)
        if hasattr(addr, 'ipv4_mapped') and addr.ipv4_mapped:
            if _is_private_or_loopback(addr.ipv4_mapped):
                return False
        return True
    except ValueError:
        pass  # Not a raw IP — proceed to DNS resolution

    # DNS resolution with timeout to catch hostname-based SSRF
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(2)
        try:
            results = socket.getaddrinfo(hostname, None)
        finally:
            socket.setdefaulttimeout(old_timeout)
    except (socket.gaierror, socket.timeout, OSError):
        return False  # Can't resolve — block

    for family, _type, _proto, _canonname, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
            if _is_private_or_loopback(addr):
                return False
            if hasattr(addr, 'ipv4_mapped') and addr.ipv4_mapped:
                if _is_private_or_loopback(addr.ipv4_mapped):
                    return False
        except ValueError:
            return False  # Unparseable IP — block

    return True
