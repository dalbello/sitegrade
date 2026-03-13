from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("scan/", views.scan, name="scan"),
    path("create-payment-intent/", views.create_payment_intent, name="create_payment_intent"),
    path("report/<uuid:report_id>/", views.report_view, name="report"),
    path("report/<uuid:report_id>/unlock/", views.unlock_report, name="unlock_report"),
    path("report/<uuid:report_id>/pdf/", views.download_pdf, name="download_pdf"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
]
