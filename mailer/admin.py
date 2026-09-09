from django.contrib import admin

from .models import EmailMessage


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "subject",
        "status",
        "created_at",
        "sent_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "recipient",
        "subject",
    )

    readonly_fields = (
        "gmail_message_id",
        "created_at",
        "sent_at",
        "error",
    )