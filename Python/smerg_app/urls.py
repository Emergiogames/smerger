from django.urls import path
from .views import *
from . import views

urlpatterns = [
    path('login', LoginView.as_view()), # Login
    path('regotp', RegisterOtp.as_view()), # Register OTP
    path('register', RegisterView.as_view()), # User creation
    path('forgotpwd', ForgotPwd.as_view()), # Forgot password
    path('changepwd', ChangePwd.as_view()), # Change Password
    path('otpconfirm', OTPConfirm.as_view()), # OTP Confirmation
    path('get_post', SinglePostDetails.as_view()), # Single post using Id
    path('business', BusinessList.as_view()), # Business
    path('business<int:id>', BusinessList.as_view()), # Business
    path('investor', InvestorList.as_view()), # Investor
    path('investor<int:id>', InvestorList.as_view()),  # Investor
    path('franchise', FranchiseList.as_view()), # Franchise
    path('franchise<int:id>', FranchiseList.as_view()), # Franchise
    path('advisor', AdvisorList.as_view()), # Advisor
    path('advisor<int:id>', AdvisorList.as_view()), # Advisor
    path('edit_posts<int:id>', EditPosts.as_view()), # Edit posts
    path('contact', Contact.as_view()), # Contact Us
    path('search', Search.as_view()), # Search
    path('user', UserView.as_view()), # User information
    path('wishlist', Wishlists.as_view()), # Wishlist
    path('recent', RecentActs.as_view()), # Recent Activities
    path('suggest', Suggests.as_view()), # Suggestions
    path('testimonial', Testimonials.as_view()), # Testimonials
    path('testimonial<int:id>', Testimonials.as_view()), # Testimonials
    path('activity', Transactions.as_view()), # Recent Transactions
    path('social', Social.as_view()), # Social
    path('banner', Banners.as_view()), # Banners
    path('prefer', Prefer.as_view()),
    path('prefer/<int:id>', Prefer.as_view()), # Preferred
    path('plans', Plans.as_view()), # Plans
    path('order_fetch', RazorOrder.as_view()), # Razor Pay order
    path('subscribe', Subscribe.as_view()), # Subscriptions
    path('recommended', Recommended.as_view()), # Recommended Posts
    path('featured', Featured.as_view()), # Featured Posts
    path('latest', Latest.as_view()), # Latest Posts
    path('notification', Notifications.as_view()), # Notification Posts
    path('notification<int:id>', Notifications.as_view()), # Notification Posts
    path('graph', Graph.as_view()), # Graph
    path('userid', User.as_view()), # User Id passing
    path('onesignal', OneSignal.as_view()), # OneSignal Id updating
    path('popularsearch', Popularsearch.as_view()), #popular searched posts
    path('popularsearch<int:id>', Popularsearch.as_view()),# popular searched posts
    # path('recentsearchview', RecentSearchview.as_view()), #recently viewed posts
    # path('recentsearchview<int:id>', RecentSearchview.as_view()),# recently viewed posts
    path('report', ReportPost.as_view()), # Report the post
    path('recent_enquiries', RecentEnquiries.as_view()), # recent enquiries
    path('count_enquiries', EnquiriesCounts.as_view()), # count of recent enquires
    path('filter_posts',  FilterPosts.as_view()), # Filter data from posts
    path('aadhaar',  AadharInfo.as_view()), # Save aadhar data
]