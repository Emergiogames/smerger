from django.core.management.base import BaseCommand
from smerg_app.models import *
from django.utils import timezone
from datetime import timedelta, datetime

# Task creation for deleting PLAN SUBSCRIPTION, DEACTIVATED USERS, BANNER VALIDATION on EXPIRY (Need to be updated at/ before 11.59)
class Command(BaseCommand):
    help = 'Update Daily'
    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        print(f"Cron working : {today}")
        Subscription.objects.filter(expiry_date=today).delete()

        Banner.objects.filter(validity_date=today).delete()

        cutoff_date = today - timedelta(days=30)
        deactivated = UserProfile.objects.filter(deactivate=True, deactivated_on__lte=cutoff_date).delete()