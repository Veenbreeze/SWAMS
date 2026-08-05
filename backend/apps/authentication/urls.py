from django.urls import path

from apps.authentication import views

urlpatterns = [
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("refresh", views.TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("logout-all", views.LogoutAllView.as_view(), name="auth-logout-all"),
    path("change-password", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path(
        "me/profile-picture",
        views.MyProfilePictureView.as_view(),
        name="auth-me-profile-picture",
    ),
    path(
        "password-reset/request",
        views.PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "password-reset/confirm",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
