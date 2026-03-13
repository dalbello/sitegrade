# Blog Post for tinyship.ai/blog/

slug: sitegrade-launch
title: SiteGrade: Stop Running 5 Different Tools to Check Your Website's Health
excerpt: One URL. Seven real-time checks. A-F grade in seconds. We built SiteGrade to replace the fragmented mess of SSL checkers, header analyzers, and performance tools.

---

Every time you need to check a website's health, you end up bouncing between SSL Labs, securityheaders.com, GTmetrix, BuiltWith, and a DNS lookup tool. Five tabs. Five different interfaces. Five sets of results you have to mentally combine.

We built [SiteGrade](https://sitegrade.tinyship.ai) to fix that.

## What It Does

Paste any URL and get an instant A+ to F grade across six categories:

- **SSL Certificate** — issuer, expiry, days remaining, protocol, cipher strength
- **Security Headers** — HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- **Performance** — TTFB, page size, redirects, gzip/brotli compression
- **Tech Stack** — CMS, framework, CDN, analytics, server detection from headers and HTML
- **DNS Health** — A/AAAA/MX/NS records, SPF, DMARC
- **Mobile Ready** — viewport meta, responsive indicators, touch icons, media queries

The free scan shows your grades. For $1.99, unlock the full detailed report with specific findings and a downloadable PDF you can hand to a client or boss.

## Not Another AI Wrapper

SiteGrade makes real network connections. It performs actual SSL handshakes, sends live HTTP requests, resolves DNS records, and parses HTML. No AI, no estimates, no "based on typical sites like yours." Every data point comes from testing your site directly.

You literally cannot get this information from ChatGPT — it can't open a socket to your server and check when your SSL certificate expires.

## The Client-Ready PDF

The $1.99 report generates a professional PDF with:
- Overall grade prominently displayed
- Score table across all categories
- Detailed findings per section with ✓/✗ indicators
- Specific fix recommendations for every issue found

Email it to your client. Put it in a slide deck. Use it in a proposal. That's the point.

## Try It

Head to [sitegrade.tinyship.ai](https://sitegrade.tinyship.ai), paste a URL, and see how your site scores. The grade is free. The details are $1.99.
