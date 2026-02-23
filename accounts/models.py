from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

# Single signal that handles both creation and saving
@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    """
    Create or update user profile when User is saved.
    Handles both new users and existing users without profiles.
    """
    if created:
        # For new users, create profile
        Profile.objects.create(user=instance)
    else:
        # For existing users, try to get or create profile
        try:
            # Try to access existing profile
            instance.profile.save()
        except (Profile.DoesNotExist, AttributeError):
            # Profile doesn't exist, create it
            Profile.objects.create(user=instance)   