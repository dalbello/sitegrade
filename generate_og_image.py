#!/usr/bin/env python3
"""Generate OG image for SiteGrade."""
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


def generate_og_image(output_path="static/img/og-image.png"):
    width, height = 1200, 630
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Dark gradient background
    for y in range(height):
        r = int(3 + (y / height) * 10)
        g = int(7 + (y / height) * 15)
        b = int(12 + (y / height) * 20)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Green accent bar at top
    draw.rectangle([(0, 0), (width, 6)], fill=(16, 185, 129))

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except (OSError, IOError):
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.text((60, 70), "SiteGrade", fill=(16, 185, 129), font=title_font)
    draw.text((60, 145), "Instant Website Health Report", fill="white", font=sub_font)
    draw.text((60, 195), "7 real-time checks. 1 click. A+ to F grade.", fill=(156, 163, 175), font=small_font)

    features = [
        "SSL Certificate & Cipher Analysis",
        "Security Headers (HSTS, CSP, X-Frame)",
        "Performance (TTFB, Size, Compression)",
        "Tech Stack Detection",
        "DNS Health + SPF/DMARC",
        "Mobile Readiness Check",
    ]
    y_pos = 275
    for feat in features:
        draw.text((80, y_pos), f"✓  {feat}", fill=(209, 250, 229), font=small_font)
        y_pos += 38

    draw.text((60, height - 60), "sitegrade.tinyship.ai", fill=(107, 114, 128), font=small_font)
    draw.text((width - 180, height - 60), "$1.99/report", fill=(16, 185, 129), font=small_font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"✅ OG image saved to {output_path}")


if __name__ == "__main__":
    generate_og_image()
