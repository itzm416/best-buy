from authenticationapp import views
from django.urls import path

urlpatterns = [
    path('register/', views.register_view, name='register'),

    path('mfa/', views.mfa_view, name='mfa'),
    path('verify-mfa/', views.verify_mfa, name='verify-mfa'),
    path('disable-2fa/', views.disable_mfa, name='disable-2fa'),

    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password_view, name="change-password"),
    path("password-reset/", views.password_reset_view, name="password-reset"),
    path("password-reset-confirm/<str:uidb64>/<str:token>/", views.password_reset_confirm_view, name="password-reset-confirm"),
    path('activate/<str:uidb64>/<str:token>/', views.activate_account, name='activate'),


    path('account-setting/', views.account_setting, name='account-setting'),

]
