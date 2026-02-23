from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Email verification URLs
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('verification-sent/', views.verification_sent, name='verification_sent'),
    path('verification-success/', views.verification_success, name='verification_success'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    
    # Password reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
]