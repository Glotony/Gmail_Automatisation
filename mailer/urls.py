from django.urls import path

from .views import (
    EmailHistoryView,
    SendEmailView,
)


urlpatterns = [
    path(
        "send/",
        SendEmailView.as_view(),
        name="send-email",
    ),

    path(
        "history/",
        EmailHistoryView.as_view(),
        name="email-history",
    ),
]