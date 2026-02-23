from django.db import models
from django.contrib.auth.models import User


class Contract(models.Model):
    RISK_LEVELS = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts')
    filename = models.CharField(max_length=255)
    raw_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    overall_risk_score = models.IntegerField(default=0)
    overall_risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='Low')
    analysis_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.user.username})"


class Risk(models.Model):
    SEVERITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('accepted', 'Accepted'),
        ('disputed', 'Disputed'),
    ]

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='risks')
    risk_id = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    category = models.CharField(max_length=100)
    clause = models.TextField(blank=True)
    explanation = models.TextField()
    recommendation = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user_note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.severity}"
