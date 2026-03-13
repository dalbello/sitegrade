import uuid
from django.db import models


class SiteReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=500)
    domain = models.CharField(max_length=255)
    overall_grade = models.CharField(max_length=2, blank=True)
    overall_score = models.IntegerField(default=0)

    # Individual category scores (0-100)
    ssl_score = models.IntegerField(default=0)
    headers_score = models.IntegerField(default=0)
    performance_score = models.IntegerField(default=0)
    techstack_score = models.IntegerField(default=0)
    dns_score = models.IntegerField(default=0)
    mobile_score = models.IntegerField(default=0)

    # Raw JSON results for each category
    ssl_data = models.JSONField(default=dict)
    headers_data = models.JSONField(default=dict)
    performance_data = models.JSONField(default=dict)
    techstack_data = models.JSONField(default=dict)
    dns_data = models.JSONField(default=dict)
    mobile_data = models.JSONField(default=dict)

    # Payment
    paid = models.BooleanField(default=False)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.domain} — {self.overall_grade} ({self.created_at:%Y-%m-%d %H:%M})"
