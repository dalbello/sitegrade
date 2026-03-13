import json
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import SiteReport
from .scanner import run_full_scan, normalize_url
from .pdf_report import generate_pdf


def home(request):
    """Landing page with URL input."""
    context = {
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }
    if request.user.is_authenticated and request.user.is_staff:
        context["staff_bypass"] = True
    return render(request, "home.html", context)


@require_POST
def scan(request):
    """Run the scan and return preview results (free) or full results (paid/staff)."""
    url_input = request.POST.get("url", "").strip()
    if not url_input:
        return JsonResponse({"error": "Please enter a URL"}, status=400)

    try:
        _, domain = normalize_url(url_input)
    except ValueError:
        return JsonResponse({"error": "Invalid URL. Please enter a valid website address."}, status=400)

    try:
        results = run_full_scan(url_input)
    except Exception as e:
        return JsonResponse({"error": f"Scan failed: {str(e)[:200]}"}, status=500)

    # Save report
    report = SiteReport.objects.create(
        url=results["url"],
        domain=results["domain"],
        overall_grade=results["overall_grade"],
        overall_score=results["overall_score"],
        ssl_score=results["scores"]["ssl"],
        headers_score=results["scores"]["headers"],
        performance_score=results["scores"]["performance"],
        techstack_score=results["scores"]["techstack"],
        dns_score=results["scores"]["dns"],
        mobile_score=results["scores"]["mobile"],
        ssl_data=results["ssl"],
        headers_data=results["headers"],
        performance_data=results["performance"],
        techstack_data=results["techstack"],
        dns_data=results["dns"],
        mobile_data=results["mobile"],
    )

    # Staff bypass = auto-paid
    is_staff = request.user.is_authenticated and request.user.is_staff
    if is_staff:
        report.paid = True
        report.save()

    response_data = {
        "report_id": str(report.id),
        "domain": results["domain"],
        "overall_grade": results["overall_grade"],
        "overall_score": results["overall_score"],
        "scores": results["scores"],
        "paid": report.paid,
    }

    # Free preview: just scores. Paid/staff: full details
    if report.paid:
        response_data["details"] = {
            "ssl": results["ssl"],
            "headers": results["headers"],
            "performance": results["performance"],
            "techstack": results["techstack"],
            "dns": results["dns"],
            "mobile": results["mobile"],
        }

    return JsonResponse(response_data)


@require_POST
def create_payment_intent(request):
    """Create Stripe PaymentIntent for $1.99."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    report_id = request.POST.get("report_id", "")
    try:
        intent = stripe.PaymentIntent.create(
            amount=199,  # $1.99
            currency="usd",
            metadata={"product": "sitegrade_report", "report_id": report_id},
        )
        return JsonResponse({"clientSecret": intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def unlock_report(request, report_id):
    """Mark report as paid (called after successful payment) and return full details."""
    report = get_object_or_404(SiteReport, id=report_id)
    payment_intent = request.GET.get("payment_intent", "")

    if payment_intent:
        report.paid = True
        report.stripe_payment_intent = payment_intent
        report.save()

    if not report.paid:
        return JsonResponse({"error": "Payment required"}, status=402)

    return JsonResponse({
        "report_id": str(report.id),
        "domain": report.domain,
        "overall_grade": report.overall_grade,
        "overall_score": report.overall_score,
        "scores": {
            "ssl": report.ssl_score,
            "headers": report.headers_score,
            "performance": report.performance_score,
            "techstack": report.techstack_score,
            "dns": report.dns_score,
            "mobile": report.mobile_score,
        },
        "paid": True,
        "details": {
            "ssl": report.ssl_data,
            "headers": report.headers_data,
            "performance": report.performance_data,
            "techstack": report.techstack_data,
            "dns": report.dns_data,
            "mobile": report.mobile_data,
        },
    })


def download_pdf(request, report_id):
    """Download PDF report (paid only)."""
    report = get_object_or_404(SiteReport, id=report_id)
    if not report.paid:
        return HttpResponse("Payment required for PDF download", status=402)

    report_data = {
        "domain": report.domain,
        "overall_grade": report.overall_grade,
        "overall_score": report.overall_score,
        "scores": {
            "ssl": report.ssl_score,
            "headers": report.headers_score,
            "performance": report.performance_score,
            "techstack": report.techstack_score,
            "dns": report.dns_score,
            "mobile": report.mobile_score,
        },
        "ssl": report.ssl_data,
        "headers": report.headers_data,
        "performance": report.performance_data,
        "techstack": report.techstack_data,
        "dns": report.dns_data,
        "mobile": report.mobile_data,
    }

    pdf_bytes = generate_pdf(report_data)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="sitegrade-{report.domain}.pdf"'
    return response


def report_view(request, report_id):
    """Public report page."""
    report = get_object_or_404(SiteReport, id=report_id)
    score_list = [
        ("SSL Certificate", "ssl", report.ssl_score, "🔒"),
        ("Security Headers", "headers", report.headers_score, "🛡️"),
        ("Performance", "performance", report.performance_score, "🚀"),
        ("Tech Stack", "techstack", report.techstack_score, "🔧"),
        ("DNS Health", "dns", report.dns_score, "🌐"),
        ("Mobile Ready", "mobile", report.mobile_score, "📱"),
    ]
    context = {
        "report": report,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "score_list": score_list,
    }
    if report.paid:
        context["details"] = {
            "ssl": report.ssl_data,
            "headers": report.headers_data,
            "performance": report.performance_data,
            "techstack": report.techstack_data,
            "dns": report.dns_data,
            "mobile": report.mobile_data,
        }
    if request.user.is_authenticated and request.user.is_staff:
        context["staff_bypass"] = True
    return render(request, "report.html", context)


def privacy(request):
    return render(request, "privacy.html")


def terms(request):
    return render(request, "terms.html")
