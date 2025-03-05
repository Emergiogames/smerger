from django.db import models
from django.contrib.auth.models import *
import random, string
from django.utils import timezone
from custom_storages import MediaStorage
from django.utils.timezone import now

class CustomUserManager(UserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)
    
    def make_random_password(self, length=10, allowed_chars=string.ascii_letters + string.digits + string.punctuation):
        return ''.join(random.choice(allowed_chars) for _ in range(length))

class UserProfile(AbstractUser):
    image = models.FileField(storage=MediaStorage(),upload_to='profile/images', null=True, blank=True)
    onesignal_id = models.CharField(max_length=100, null=True, blank=True)
    block = models.BooleanField(default=False)
    total_hr_spend = models.FloatField(default=0.0)
    active_from = models.DateTimeField(null=True, blank=True)
    inactive_from = models.DateTimeField(null=True, blank=True)
    deactivate = models.BooleanField(default=False)
    deactivated_on = models.DateField(null=True, blank=True)
    verified = models.BooleanField(default=False) ## Aadhar verification
    mobile_device = models.CharField(max_length=500, null=True, blank=True)
    web_device = models.CharField(max_length=500, null=True, blank=True)

    objects = CustomUserManager()

# class Profile(models.Model):
#     user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
#     name = models.CharField(max_length=100)
#     number = models.CharField(max_length=17)
#     email = models.EmailField(max_length=254)
#     industry = models.CharField(max_length=100)
#     web_url = models.CharField(max_length=200, blank=True, null=True)
#     state = models.CharField(max_length=100)
#     city = models.CharField(max_length=100)
#     image = models.ImageField(storage=MediaStorage(),upload_to='profile_images/', blank=True, null=True)
#     experiance = models.CharField(max_length=500, blank=True, null=True)
#     about = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     type = models.CharField(max_length=100)
#     aadhar_verified = models.BooleanField(default=False)
#     interest = models.CharField(max_length=500, blank=True, null=True)

# Business, Investor, Franchise posts
class SaleProfiles(models.Model):
    ENTITY_TYPE_CHOICES = [
        ('business', 'Business'),
        ('investor', 'Investor'),
        ('franchise', 'Franchise'),
        ('advisor', 'Advisor'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    title = models.TextField(default='', null=True, blank=True)
    single_desc = models.TextField(default='', null=True, blank=True)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    impressions = models.IntegerField(default=0)

    # Common fields
    industry = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    url = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    establish_yr = models.CharField(max_length=100, null=True, blank=True)
    ebitda = models.IntegerField(null=True, blank=True)
    listed_on = models.DateTimeField(auto_now=True)
    range_starting = models.IntegerField(null=True, blank=True)
    range_ending = models.IntegerField(null=True, blank=True)

    # Business-specific fields
    type_sale = models.CharField(max_length=1000, null=True, blank=True)
    address_1 = models.TextField(null=True, blank=True)
    address_2 = models.TextField(null=True, blank=True)
    pin = models.IntegerField(null=True, blank=True)
    employees = models.IntegerField(default=0, null=True, blank=True)
    avg_monthly = models.IntegerField(null=True, blank=True)
    latest_yearly = models.IntegerField(null=True, blank=True)
    entity = models.CharField(max_length=100, null=True, blank=True)
    features = models.TextField(null=True, blank=True)
    facility = models.TextField(null=True, blank=True)
    top_selling = models.TextField(null=True, blank=True)
    income_source = models.TextField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    asking_price = models.CharField(max_length=100,null=True,blank=True)

    # Investor-specific fields
    company = models.CharField(max_length=100, null=True, blank=True)
    location_interested = models.TextField(null=True, blank=True)
    evaluating_aspects = models.TextField(null=True, blank=True)
    preference = models.JSONField(null=True, blank=True)
    profile_summary = models.TextField(null=True,blank=True)

    # Franchise-specific fields
    initial = models.IntegerField(null=True, blank=True)
    proj_ROI = models.CharField(max_length=100, null=True, blank=True)
    avg_monthly_sales = models.IntegerField(null=True, blank=True)
    locations_available = models.CharField(max_length=1000, null=True, blank=True)
    offering = models.TextField(null=True, blank=True)
    total_outlets = models.TextField(null=True, blank=True)
    yr_period = models.CharField(max_length=100, null=True, blank=True)
    supports = models.TextField(null=True, blank=True)
    services = models.TextField(null=True, blank=True)
    min_space = models.IntegerField(null=True, blank=True)
    max_space = models.IntegerField(null=True, blank=True)
    brand_fee = models.IntegerField(null=True, blank=True)
    staff = models.IntegerField(null=True, blank=True)

    # Advisor-specific fields
    number = models.CharField(max_length=17, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    interest = models.CharField(max_length=500, blank=True, null=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    experience = models.CharField(null=True, blank=True, max_length=100)

    # Common file fields
    profile = models.FileField(storage=MediaStorage(), upload_to='combined/images/profile', null=True, blank=True)
    logo = models.FileField(storage=MediaStorage(), upload_to='combined/images', null=True, blank=True)
    image1 = models.FileField(storage=MediaStorage(), upload_to='combined/images', null=True, blank=True)
    image2 = models.FileField(storage=MediaStorage(), upload_to='combined/images', null=True, blank=True)
    image3 = models.FileField(storage=MediaStorage(), upload_to='combined/images', null=True, blank=True)
    image4 = models.FileField(storage=MediaStorage(), upload_to='combined/images', null=True, blank=True)
    doc1 = models.FileField(storage=MediaStorage(), upload_to='combined/docs', null=True, blank=True)
    doc2 = models.FileField(storage=MediaStorage(), upload_to='combined/docs', null=True, blank=True)
    doc3 = models.FileField(storage=MediaStorage(), upload_to='combined/docs', null=True, blank=True)
    doc4 = models.FileField(storage=MediaStorage(), upload_to='combined/docs', null=True, blank=True)
    proof1 = models.FileField(storage=MediaStorage(), upload_to='combined/proof', null=True, blank=True)
    proof2 = models.FileField(storage=MediaStorage(), upload_to='combined/proof', null=True, blank=True)
    proof3 = models.FileField(storage=MediaStorage(), upload_to='combined/proof', null=True, blank=True)
    proof4 = models.FileField(storage=MediaStorage(), upload_to='combined/proof', null=True, blank=True)

    # Booleens
    block = models.BooleanField(default=False)
    verified = models.BooleanField(default=False) ## Admin verification
    subscribed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.entity_type})"

# Contact Us
class Query(models.Model):
    firstname = models.CharField(max_length=1000)
    lastname = models.CharField(max_length=1000)
    email = models.EmailField(max_length=1000)
    number = models.CharField(max_length=1000)
    message = models.TextField()

# Wishlist items
class Wishlist(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(SaleProfiles, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"

# Recent Activity
class RecentActivity(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(SaleProfiles, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Recent Activity"

# Suggestions
class Suggestion(models.Model):
    user = models.ForeignKey(UserProfile,on_delete=models.CASCADE)
    suggestions = models.TextField()

# Testimonials
class Testimonial(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    advisor = models.ForeignKey(SaleProfiles, on_delete=models.CASCADE, null=True, blank=True)
    rate = models.IntegerField(default=0)
    testimonial = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

# Log of datas
class ActivityLog(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=500,default="")
    action = models.CharField(max_length=255)
    title = models.CharField(max_length=500)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    img = models.FileField(storage=MediaStorage(),upload_to='combined/images',null=True, blank=True)
    rate = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.action}"

# Event/ Offer Banners
class Banner(models.Model):
    img = models.FileField(storage=MediaStorage(), upload_to='banners/images')
    type = models.CharField(max_length=100, choices=[('business', 'Business'), ('advisor', 'Advisor'), ('franchise', 'Franchise'), ('investor', 'Investor'),('all','All')])
    created_date = models.DateTimeField(auto_now_add=True)
    validity_date = models.DateField()

# Questionaires / User preference
class Preference(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    profile = models.CharField(max_length=500)
    city = models.CharField(max_length=500, null=True, blank=True)
    state = models.CharField(max_length=500, null=True, blank=True)
    interested_city = models.JSONField(null=True, blank=True)
    interested_state = models.JSONField(null=True, blank=True)
    industries = models.JSONField(null=True, blank=True)
    budget = models.CharField(max_length=500, null=True, blank=True)
    price_starting = models.CharField(max_length=500, null=True, blank=True)
    price_ending = models.CharField(max_length=500, null=True, blank=True)
    frequency = models.CharField(max_length=500, null=True, blank=True)
    type = models.CharField(max_length=500, null=True, blank=True) 

    ## Business
    business_stage = models.CharField(max_length=500, null=True, blank=True)
    business_goal = models.CharField(max_length=500, null=True, blank=True)
    business_duration = models.CharField(max_length=500, null=True, blank=True)

    ## Investor
    investment_interest = models.CharField(max_length=500, null=True, blank=True)
    investment_horizon = models.CharField(max_length=500, null=True, blank=True)
    risk_tolerence = models.CharField(max_length=500, null=True, blank=True)
    investment_experiance = models.CharField(max_length=500, null=True, blank=True)
    
    ## Franchise
    buy_start = models.CharField(max_length=500, null=True, blank=True)
    franchise_type = models.CharField(max_length=500, null=True, blank=True)
    franchise_brands = models.CharField(max_length=500, null=True, blank=True)

    ## Advisor
    expertise = models.CharField(max_length=500, null=True, blank=True)
    client_type = models.CharField(max_length=500, null=True, blank=True)
    advisor_experiance = models.CharField(max_length=500, null=True, blank=True)
    advisory_duration = models.CharField(max_length=500, null=True, blank=True)

# Plans
class Plan(models.Model):
    TYPE_CHOICES = [
        ('business', 'Business'),
        ('investor', 'Investor'),
        ('franchise', 'Franchise'),
        ('advisor', 'Advisor'),
    ]

    name = models.CharField(max_length=100)
    rate = models.IntegerField(default=0)
    description = models.JSONField()
    time_period = models.IntegerField(default=0)
    post_number = models.IntegerField()
    feature = models.BooleanField(default=False)
    recommend = models.BooleanField(default=False)
    type = models.CharField(max_length=100, choices=TYPE_CHOICES)

# User plan subscriptions
class Subscription(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    expiry_date = models.DateField()
    remaining_posts = models.IntegerField()
    transaction_id = models.CharField(max_length=100)
    subscribed_on = models.DateField(auto_now=True)

# Notification datas
class Notification(models.Model):
    user = models.ManyToManyField(UserProfile, related_name='notifications')
    title =  models.CharField(max_length=100)
    description = models.TextField()    
    image = models.FileField(storage=MediaStorage(),upload_to='notification/image',null=True,blank=True)
    url = models.URLField(max_length=200,null=True,blank=True)
    created_on = models.DateTimeField(auto_now=True)
    read_by = models.ManyToManyField(UserProfile, related_name='read_notifications', blank=True)

# For Popular searched items and recently Searched items
class Activity(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True)
    post = models.ForeignKey(SaleProfiles, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now=True)
    count = models.PositiveIntegerField(default=1,null=True)

# Enquiries on a post
class Enquiries(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True)
    post = models.ForeignKey(SaleProfiles, on_delete=models.CASCADE)
    room_id = models.IntegerField(default=0, null=True, blank=True)
    created = models.DateTimeField(auto_now=True)

# Report model
class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('post', 'Post'),
        ('profile', 'Profile'),
    ]

    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
    ]

    report_post = models.ForeignKey(SaleProfiles, on_delete=models.CASCADE, null=True, blank=True)
    reported_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='userprofile_reported')
    reason = models.TextField(null=True, blank=True)
    reason_type = models.CharField(max_length=255)
    reported_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)  # Add choices for report type
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')  # Add status field
    created_at = models.DateField(auto_now_add=True, null=True)  # Allow null initially

    def __str__(self):
        return f"Report for {self.reported_profile or self.report_post} - {self.status}"

    def __init__(self, *args, **kwargs):
        self.sale_profile_id = kwargs.pop('sale_profile_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

class UserSession(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(null=True, blank=True)
    session_duration = models.IntegerField(null=True, blank=True)  # Store duration in seconds

    def save(self, *args, **kwargs):
        # Calculate session duration when logout_time is set
        if self.logout_time:
            self.session_duration = int((self.logout_time - self.login_time).total_seconds())
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.user} - {self.session_duration}s"

class AadhaarDetails(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=50)
    number = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=50, null=True, blank=True)
    dob = models.CharField(max_length=50, null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    address = models.JSONField(null=True, blank=True)
    profile_image = models.ImageField(upload_to="aadhaar/image", null=True, blank=True)