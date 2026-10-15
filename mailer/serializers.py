import base64
import binascii
from pathlib import Path

from rest_framework import serializers

from .models import EmailMessage

MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 18 * 1024 * 1024


class SubjectSectionSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)


class ApplicationSectionSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=False)


class AttachmentPayloadSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255, allow_blank=False)
    mime_type = serializers.CharField(max_length=127, allow_blank=False)
    content_base64 = serializers.CharField(allow_blank=False, trim_whitespace=False)

    def validate_filename(self, value):
        if Path(value).name != value or any(char in value for char in ("/", "\\", "\r", "\n")):
            raise serializers.ValidationError("Filename must not contain a path.")
        return value

    def validate_mime_type(self, value):
        if value.count("/") != 1:
            raise serializers.ValidationError("MIME type must be in type/subtype format.")
        main_type, sub_type = value.split("/", 1)
        if not main_type or not sub_type or any(char.isspace() for char in value):
            raise serializers.ValidationError("Invalid MIME type.")
        return value

    def validate_content_base64(self, value):
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise serializers.ValidationError("Attachment content is not valid base64.") from exc
        if len(decoded) > MAX_ATTACHMENT_BYTES:
            raise serializers.ValidationError("Each attachment must be 15 MiB or smaller.")
        return value


class SendEmailSerializer(serializers.Serializer):
    recipient = serializers.EmailField()
    subject = SubjectSectionSerializer()
    application = ApplicationSectionSerializer()
    files = serializers.DictField(
        child=AttachmentPayloadSerializer(),
        required=False,
        default=dict,
    )
    links = serializers.DictField(
        child=serializers.URLField(),
        required=False,
        default=dict,
    )

    def validate_links(self, links):
        for name, url in links.items():
            if not url.startswith(("http://", "https://")):
                raise serializers.ValidationError(
                    {name: "Only http:// and https:// links are accepted."}
                )
        return links

    def validate_files(self, files):
        total_size = 0
        for attachment in files.values():
            try:
                total_size += len(base64.b64decode(attachment["content_base64"], validate=True))
            except (binascii.Error, ValueError) as exc:
                raise serializers.ValidationError("Attachment content is not valid base64.") from exc
        if total_size > MAX_TOTAL_ATTACHMENT_BYTES:
            raise serializers.ValidationError("Combined attachments must be 18 MiB or smaller.")
        return files


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
