from django.utils import timezone

from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmailMessage
from .permissions import HasAPIKey
from .serializers import EmailMessageSerializer, SendEmailSerializer
from .services import compose_body, send_email


class SendEmailView(APIView):
    permission_classes = [HasAPIKey]
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]

    def post(self, request):
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        recipient = data["recipient"]
        subject = data["subject"]["text"]
        body = compose_body(
            data["application"]["message"],
            data.get("links", {}),
        )
        attachments = data.get("files", {})

        email_record = EmailMessage.objects.create(
            recipient=recipient,
            subject=subject,
            message=body,
            status=EmailMessage.Status.FAILED,
        )

        try:
            gmail_message_id = send_email(
                recipient=recipient,
                subject=subject,
                body=body,
                attachments=attachments,
            )
        except Exception as exc:
            email_record.error = str(exc)
            email_record.save(update_fields=["error"])
            return Response(
                {
                    "status": "failed",
                    "id": email_record.id,
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        email_record.status = EmailMessage.Status.SENT
        email_record.gmail_message_id = gmail_message_id
        email_record.sent_at = timezone.now()
        email_record.save(
            update_fields=["status", "gmail_message_id", "sent_at"]
        )
        return Response(
            {
                "status": "sent",
                "id": email_record.id,
                "gmail_message_id": gmail_message_id,
                "attachments_sent": [
                    attachment["filename"] for attachment in attachments.values()
                ],
            },
            status=status.HTTP_201_CREATED,
        )


class EmailHistoryView(APIView):
    permission_classes = [HasAPIKey]
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        messages = EmailMessage.objects.all()
        serializer = EmailMessageSerializer(messages, many=True)
        return Response(serializer.data)
