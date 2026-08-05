from django.urls import path

from apps.subscriptions import views

urlpatterns = [
    path(
        "subscriptions/plans",
        views.SubscriptionPlanListCreateView.as_view(),
        name="subscription-plans",
    ),
    path(
        "subscriptions/plans/<uuid:pk>",
        views.SubscriptionPlanDetailView.as_view(),
        name="subscription-plan-detail",
    ),
    path(
        "subscriptions",
        views.SubscriptionListCreateView.as_view(),
        name="subscriptions",
    ),
    path(
        "subscriptions/<uuid:pk>/cancel",
        views.SubscriptionCancelView.as_view(),
        name="subscription-cancel",
    ),
    path(
        "subscriptions/expiry-monitor",
        views.SubscriptionExpiryMonitorView.as_view(),
        name="subscription-expiry-monitor",
    ),
]
