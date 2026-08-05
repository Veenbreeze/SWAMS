from django.urls import path

from apps.feedback import views

urlpatterns = [
    path(
        "recommendations",
        views.RecommendationListCreateView.as_view(),
        name="recommendations",
    ),
]
