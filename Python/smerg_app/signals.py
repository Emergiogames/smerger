from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *
from django.utils import timezone
from smerg_chat.models import Room, ChatMessage
from smerg_chat.utils.enc_utils import encrypt_message

@receiver(post_save, sender=UserProfile)
def log_model_save(sender, instance, created, **kwargs):
    if created:

        ## Generate room with admin for chatting
        admin = UserProfile.objects.filter(is_superuser=True).first()
        message = "Welcome to Investryx! We're thrilled to have you on board. Feel free to reach out to us anytime for assistance, guidance, or a friendly chat. Let's achieve great things together!"
        room = Room.objects.create(first_person=instance, second_person=admin, last_msg=encrypt_message(message[:30]))
        ChatMessage.objects.create(sended_by=admin, sended_to=instance, message=encrypt_message(message), room=room)

@receiver(post_save, sender=SaleProfiles)
def log_model_save(sender, instance, created, **kwargs):
    action = "Created" if created else "Updated"
    if created:

        ## Check and update subscription
        if Subscription.objects.filter(user = instance.user, plan__type = instance.entity_type.lower()).exists() and Subscription.objects.get(user = instance.user, plan__type = instance.entity_type.lower()).remaining_posts != 0:
            instance.subscribed = False
            instance.save()
            subscribe = Subscription.objects.get(user = instance.user, plan__type = instance.entity_type.lower())
            subscribe.remaining_posts -= 1
            subscribe.save()

        ## Create Activity Log
        ActivityLog.objects.create(
            user = instance.user,
            action = action,
            title = "New Post Published",
            description = f"{instance.name} has just published an exciting new post! Dive into their latest content to see what's new and stay engaged with their updates.",
            rate = instance.range_starting,
            img = instance.user.image,
            username = instance.user.first_name
        )

# Signal for updating posts after a subscription is brought
@receiver(post_save, sender=Subscription)
def log_model_save(sender, instance, created, **kwargs):
    # updating unsubscribed posts
    posts = SaleProfiles.objects.filter(user=instance.user, entity_type=instance.plan.type, subscribed=False).order_by('id')[:instance.remaining_posts]
    post_ids = [post.id for post in posts]
    if post_ids:
        SaleProfiles.objects.filter(id__in=post_ids).update(subscribed=True)

        # updating remaining posts count
        instance.remaining_posts = max(0, instance.remaining_posts - posts.count())
        instance.save()