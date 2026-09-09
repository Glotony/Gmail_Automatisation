from rest_framework import serializers

from .models import EmailMessage


class SendEmailSerializer(serializers.Serializer):
    recipient = serializers.EmailField()

    subject = serializers.CharField(
        max_length=255
    )

    message = serializers.CharField(
        allow_blank=False
    )


class EmailMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessage

        fields = [
            "id",
            "recipient",
            "subject",
            "message",
            "gmail_message_id",
            "status",
            "error",
            "created_at",
            "sent_at",
        ]

        read_only_fields = fields