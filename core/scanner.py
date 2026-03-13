"""
SiteGrade Scanner — performs 6 independent checks on a website.
No AI, no external APIs. Pure network analysis.
"""
import ssl
import socket
import time
import re
from urllib.parse import urlparse
from datetime import datetime, timezone

import requests
import dns.resolver
from bs4 import BeautifulSoup


TIMEOUT = 10


def normalize_url(raw_url):
    """Ensure URL has scheme, return cleaned URL and domain."""
    raw_url = raw_url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    parsed = urlparse(raw_url)
    domain = parsed.hostname
    if not domain:
        raise ValueError("Invalid URL")
    return raw_url, domain


# ─── 1. SSL Certificate ──────────────────────────────────────────────────────

def check_ssl(domain):
    """Check SSL certificate details."""
    result = {
        "valid": False,
        "issuer": "",
        "subject": "",
        "expires": "",
        "days_remaining": 0,
        "protocol": "",
        "serial": "",
        "issues": [],
    }
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(TIMEOUT)
            s.connect((domain, 443))
            cert = s.getpeercert()
            cipher = s.cipher()

            # Parse expiry
            not_after = cert.get("notAfter", "")
            expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_remaining = (expire_date - datetime.now(timezone.utc)).days

            # Parse issuer
            issuer_parts = dict(x[0] for x in cert.get("issuer", []))
            subject_parts = dict(x[0] for x in cert.get("subject", []))

            result["valid"] = True
            result["issuer"] = issuer_parts.get("organizationName", issuer_parts.get("commonName", "Unknown"))
            result["subject"] = subject_parts.get("commonName", "")
            result["expires"] = expire_date.strftime("%Y-%m-%d")
            result["days_remaining"] = days_remaining
            result["protocol"] = cipher[1] if cipher else ""
            result["cipher"] = cipher[0] if cipher else ""

            if days_remaining < 7:
                result["issues"].append("Certificate expires in less than 7 days!")
            elif days_remaining < 30:
                result["issues"].append("Certificate expires in less than 30 days")

    except ssl.SSLCertVerificationError as e:
        result["issues"].append(f"SSL verification failed: {str(e)[:100]}")
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError) as e:
        result["issues"].append(f"Could not connect on port 443: {str(e)[:100]}")

    return result


def score_ssl(data):
    if not data["valid"]:
        return 0
    score = 80
    days = data["days_remaining"]
    if days > 60:
        score += 20
    elif days > 30:
        score += 10
    elif days < 7:
        score -= 30
    return max(0, min(100, score))


# ─── 2. Security Headers ─────────────────────────────────────────────────────

SECURITY_HEADERS = {
    "Strict-Transport-Security": {"weight": 20, "label": "HSTS"},
    "Content-Security-Policy": {"weight": 20, "label": "CSP"},
    "X-Frame-Options": {"weight": 15, "label": "X-Frame-Options"},
    "X-Content-Type-Options": {"weight": 15, "label": "X-Content-Type-Options"},
    "Referrer-Policy": {"weight": 15, "label": "Referrer-Policy"},
    "Permissions-Policy": {"weight": 15, "label": "Permissions-Policy"},
}


def check_headers(url):
    """Check security headers."""
    result = {"headers_present": {}, "headers_missing": [], "raw": {}}
    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True, headers={"User-Agent": "SiteGrade/1.0"})
        for header, meta in SECURITY_HEADERS.items():
            val = resp.headers.get(header)
            if val:
                result["headers_present"][meta["label"]] = val
            else:
                result["headers_missing"].append(meta["label"])
        # Store server header for tech stack
        result["raw"]["Server"] = resp.headers.get("Server", "")
        result["raw"]["X-Powered-By"] = resp.headers.get("X-Powered-By", "")
    except requests.RequestException as e:
        result["error"] = str(e)[:200]

    return result


def score_headers(data):
    if "error" in data:
        return 0
    total = len(SECURITY_HEADERS)
    present = len(data["headers_present"])
    return int((present / total) * 100) if total else 0


# ─── 3. Performance ──────────────────────────────────────────────────────────

def check_performance(url):
    """Measure TTFB, page size, redirects, compression."""
    result = {
        "ttfb_ms": 0,
        "total_time_ms": 0,
        "page_size_kb": 0,
        "redirects": 0,
        "compression": "none",
        "issues": [],
    }
    try:
        start = time.time()
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True,
                            headers={"User-Agent": "SiteGrade/1.0", "Accept-Encoding": "gzip, deflate, br"})
        total_time = time.time() - start

        # TTFB approximation (elapsed minus content download)
        result["ttfb_ms"] = int(resp.elapsed.total_seconds() * 1000)
        result["total_time_ms"] = int(total_time * 1000)
        result["page_size_kb"] = round(len(resp.content) / 1024, 1)
        result["redirects"] = len(resp.history)
        result["status_code"] = resp.status_code

        # Check compression
        encoding = resp.headers.get("Content-Encoding", "").lower()
        if "br" in encoding:
            result["compression"] = "brotli"
        elif "gzip" in encoding:
            result["compression"] = "gzip"
        elif "deflate" in encoding:
            result["compression"] = "deflate"
        else:
            result["issues"].append("No compression detected (gzip/brotli recommended)")

        if result["ttfb_ms"] > 2000:
            result["issues"].append("TTFB is over 2 seconds — server is slow")
        if result["page_size_kb"] > 3000:
            result["issues"].append("Page is over 3MB — consider optimizing")
        if result["redirects"] > 3:
            result["issues"].append(f"{result['redirects']} redirects detected — reduce redirect chains")

    except requests.RequestException as e:
        result["error"] = str(e)[:200]

    return result


def score_performance(data):
    if "error" in data:
        return 0
    score = 100
    ttfb = data["ttfb_ms"]
    if ttfb > 3000:
        score -= 40
    elif ttfb > 2000:
        score -= 25
    elif ttfb > 1000:
        score -= 10

    size = data["page_size_kb"]
    if size > 5000:
        score -= 30
    elif size > 3000:
        score -= 20
    elif size > 1000:
        score -= 5

    if data["compression"] == "none":
        score -= 15

    if data["redirects"] > 3:
        score -= 10

    return max(0, min(100, score))


# ─── 4. Tech Stack ───────────────────────────────────────────────────────────

TECH_SIGNATURES = {
    # CMS
    "WordPress": [r'wp-content', r'wp-includes', r'/wp-json/'],
    "Shopify": [r'cdn\.shopify\.com', r'shopify\.com'],
    "Squarespace": [r'squarespace\.com', r'static\.squarespace'],
    "Wix": [r'wix\.com', r'wixstatic\.com'],
    "Drupal": [r'drupal\.js', r'/sites/default/'],
    "Joomla": [r'/media/jui/', r'Joomla'],
    "Ghost": [r'ghost\.org', r'ghost-'],
    # Frameworks
    "Next.js": [r'__next', r'_next/static'],
    "Nuxt.js": [r'__nuxt', r'_nuxt/'],
    "React": [r'react\.production', r'react-dom', r'__react'],
    "Vue.js": [r'vue\.js', r'vue\.min\.js', r'__vue'],
    "Angular": [r'ng-version', r'angular\.js'],
    "Django": [r'csrfmiddlewaretoken', r'django'],
    "Laravel": [r'laravel', r'XSRF-TOKEN'],
    "Ruby on Rails": [r'csrf-token.*authenticity', r'turbolinks'],
    # CDN
    "Cloudflare": [r'cloudflare', r'cf-ray'],
    "Akamai": [r'akamai'],
    "Fastly": [r'fastly', r'x-served-by.*cache'],
    "AWS CloudFront": [r'cloudfront\.net', r'x-amz-cf-'],
    # Analytics
    "Google Analytics": [r'google-analytics\.com', r'gtag', r'googletagmanager'],
    "Facebook Pixel": [r'connect\.facebook\.net', r'fbq\('],
    "Hotjar": [r'hotjar\.com'],
    # Server
    "Nginx": [r'nginx'],
    "Apache": [r'apache'],
    "LiteSpeed": [r'litespeed'],
    "IIS": [r'microsoft-iis'],
}


def check_techstack(url, headers_data):
    """Detect technologies from HTML content and response headers."""
    result = {"detected": [], "categories": {}}
    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True,
                            headers={"User-Agent": "SiteGrade/1.0"})
        html = resp.text.lower()
        combined = html

        # Also check headers
        server = (headers_data.get("raw", {}).get("Server", "") or "").lower()
        powered = (headers_data.get("raw", {}).get("X-Powered-By", "") or "").lower()
        combined += f" {server} {powered}"

        for tech, patterns in TECH_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    if tech not in result["detected"]:
                        result["detected"].append(tech)
                    break

    except requests.RequestException as e:
        result["error"] = str(e)[:200]

    return result


def score_techstack(data):
    # Tech stack detection is informational — score based on how much we found
    if "error" in data:
        return 50
    detected = len(data["detected"])
    if detected >= 3:
        return 100
    elif detected >= 1:
        return 80
    return 60  # Nothing detected isn't necessarily bad


# ─── 5. DNS Health ────────────────────────────────────────────────────────────

def check_dns(domain):
    """Check DNS records."""
    result = {
        "a_records": [],
        "aaaa_records": [],
        "mx_records": [],
        "ns_records": [],
        "has_spf": False,
        "has_dmarc": False,
        "has_dnssec": False,
        "issues": [],
    }

    resolver = dns.resolver.Resolver()
    resolver.timeout = TIMEOUT
    resolver.lifetime = TIMEOUT

    # A records
    try:
        answers = resolver.resolve(domain, "A")
        result["a_records"] = [str(r) for r in answers]
    except Exception:
        result["issues"].append("No A records found")

    # AAAA records (IPv6)
    try:
        answers = resolver.resolve(domain, "AAAA")
        result["aaaa_records"] = [str(r) for r in answers]
    except Exception:
        pass  # IPv6 is optional

    # MX records
    try:
        answers = resolver.resolve(domain, "MX")
        result["mx_records"] = [str(r.exchange).rstrip(".") for r in answers]
    except Exception:
        pass  # Not all domains have MX

    # NS records
    try:
        answers = resolver.resolve(domain, "NS")
        result["ns_records"] = [str(r).rstrip(".") for r in answers]
    except Exception:
        result["issues"].append("Could not resolve NS records")

    # SPF (TXT record)
    try:
        answers = resolver.resolve(domain, "TXT")
        for r in answers:
            txt = str(r).lower()
            if "v=spf1" in txt:
                result["has_spf"] = True
                break
    except Exception:
        pass

    if not result["has_spf"]:
        result["issues"].append("No SPF record found — email spoofing risk")

    # DMARC
    try:
        answers = resolver.resolve(f"_dmarc.{domain}", "TXT")
        for r in answers:
            if "v=dmarc1" in str(r).lower():
                result["has_dmarc"] = True
                break
    except Exception:
        pass

    if not result["has_dmarc"]:
        result["issues"].append("No DMARC record found — email authentication weak")

    return result


def score_dns(data):
    score = 50  # Base
    if data["a_records"]:
        score += 15
    if data["aaaa_records"]:
        score += 10
    if data["ns_records"]:
        score += 5
    if data["has_spf"]:
        score += 10
    if data["has_dmarc"]:
        score += 10
    if not data["issues"]:
        score = 100
    return max(0, min(100, score))


# ─── 6. Mobile Ready ─────────────────────────────────────────────────────────

def check_mobile(url):
    """Check mobile-readiness signals."""
    result = {
        "has_viewport": False,
        "has_responsive_meta": False,
        "has_touch_icon": False,
        "has_media_queries": False,
        "issues": [],
    }
    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True,
                            headers={"User-Agent": "SiteGrade/1.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        # Viewport meta
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport and viewport.get("content"):
            result["has_viewport"] = True
            content = viewport["content"].lower()
            if "width=device-width" in content:
                result["has_responsive_meta"] = True
            else:
                result["issues"].append("Viewport exists but missing width=device-width")
        else:
            result["issues"].append("No viewport meta tag — page won't scale on mobile")

        # Touch icon
        touch_icon = soup.find("link", attrs={"rel": re.compile(r"apple-touch-icon", re.I)})
        if touch_icon:
            result["has_touch_icon"] = True

        # Check for media queries in inline styles
        styles = soup.find_all("style")
        for style in styles:
            if style.string and "@media" in style.string:
                result["has_media_queries"] = True
                break

        # Check linked stylesheets for responsive patterns
        if not result["has_media_queries"]:
            links = soup.find_all("link", attrs={"rel": "stylesheet", "media": True})
            for link in links:
                media = link.get("media", "")
                if "max-width" in media or "min-width" in media:
                    result["has_media_queries"] = True
                    break

    except requests.RequestException as e:
        result["error"] = str(e)[:200]

    return result


def score_mobile(data):
    if "error" in data:
        return 0
    score = 0
    if data["has_viewport"]:
        score += 40
    if data["has_responsive_meta"]:
        score += 30
    if data["has_touch_icon"]:
        score += 15
    if data["has_media_queries"]:
        score += 15
    return min(100, score)


# ─── Overall Grade ────────────────────────────────────────────────────────────

WEIGHTS = {
    "ssl": 0.25,
    "headers": 0.20,
    "performance": 0.20,
    "dns": 0.15,
    "mobile": 0.10,
    "techstack": 0.10,
}


def calculate_overall(scores):
    """Calculate weighted overall score and letter grade."""
    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    overall = int(total)

    if overall >= 90:
        grade = "A+"
    elif overall >= 80:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    elif overall >= 50:
        grade = "D"
    else:
        grade = "F"

    return overall, grade


def run_full_scan(raw_url):
    """Run all 6 checks and return complete results."""
    url, domain = normalize_url(raw_url)

    # Run checks
    ssl_data = check_ssl(domain)
    headers_data = check_headers(url)
    perf_data = check_performance(url)
    techstack_data = check_techstack(url, headers_data)
    dns_data = check_dns(domain)
    mobile_data = check_mobile(url)

    # Score each
    scores = {
        "ssl": score_ssl(ssl_data),
        "headers": score_headers(headers_data),
        "performance": score_performance(perf_data),
        "techstack": score_techstack(techstack_data),
        "dns": score_dns(dns_data),
        "mobile": score_mobile(mobile_data),
    }

    overall_score, overall_grade = calculate_overall(scores)

    return {
        "url": url,
        "domain": domain,
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "scores": scores,
        "ssl": ssl_data,
        "headers": headers_data,
        "performance": perf_data,
        "techstack": techstack_data,
        "dns": dns_data,
        "mobile": mobile_data,
    }
