"""
Tests para la aplicación de Telegram Bot
"""

from django.test import TestCase
from django.conf import settings
from unittest.mock import patch, MagicMock
from telegram_bot.models import TelegramConfig, TelegramChat, TelegramMessage
from telegram_bot.services import TelegramService, TelegramNotificationService
from emails.models import ReceivedEmail
from company.models import Company


class TelegramConfigTestCase(TestCase):
    """Tests para el modelo TelegramConfig"""

    def setUp(self):
        self.config = TelegramConfig.objects.create(
            name="Test Bot", bot_token="123456789:TEST_TOKEN", is_active=True
        )

    def test_config_creation(self):
        """Test creación de configuración"""
        self.assertEqual(self.config.name, "Test Bot")
        self.assertTrue(self.config.is_active)
        self.assertEqual(str(self.config), "Bot: Test Bot (Activo)")


class TelegramChatTestCase(TestCase):
    """Tests para el modelo TelegramChat"""

    def setUp(self):
        self.chat = TelegramChat.objects.create(
            name="Test Chat",
            chat_id=123456789,
            chat_type="private",
            alert_level="all",
            email_alerts=True,
            is_active=True,
        )

    def test_chat_creation(self):
        """Test creación de chat"""
        self.assertEqual(self.chat.name, "Test Chat")
        self.assertEqual(self.chat.chat_id, 123456789)
        self.assertTrue(self.chat.email_alerts)
        self.assertEqual(str(self.chat), "Test Chat (123456789)")


class TelegramServiceTestCase(TestCase):
    """Tests para TelegramService"""

    def setUp(self):
        self.config = TelegramConfig.objects.create(
            name="Test Bot", bot_token="123456789:TEST_TOKEN", is_active=True
        )
        self.service = TelegramService(self.config)

    @patch("requests.post")
    def test_send_message_success(self, mock_post):
        """Test envío exitoso de mensaje"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123, "chat": {"id": 123456789}},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.service.send_message(123456789, "Test message")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result["result"]["message_id"], 123)

    @patch("requests.post")
    def test_get_bot_info(self, mock_post):
        """Test obtener información del bot"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "Test Bot",
                "username": "test_bot",
            },
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.service.get_bot_info()

        self.assertTrue(result.get("ok"))
        self.assertEqual(result["result"]["username"], "test_bot")


class TelegramNotificationServiceTestCase(TestCase):
    """Tests para TelegramNotificationService"""

    def setUp(self):
        self.config = TelegramConfig.objects.create(
            name="Test Bot", bot_token="123456789:TEST_TOKEN", is_active=True
        )

        self.chat = TelegramChat.objects.create(
            name="Test Chat",
            chat_id=123456789,
            chat_type="private",
            alert_level="all",
            email_alerts=True,
            is_active=True,
        )

        self.service = TelegramNotificationService()

    @patch("telegram_bot.services.TelegramService.send_message")
    def test_send_email_alert(self, mock_send_message):
        """Test envío de alerta de email"""
        # Mock response
        mock_send_message.return_value = {"ok": True, "result": {"message_id": 123}}

        results = self.service.send_email_alert(
            email_subject="Test Subject",
            email_sender="test@example.com",
            email_priority="high",
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])

        # Verificar que se creó el mensaje en la BD
        message = TelegramMessage.objects.first()
        self.assertIsNotNone(message)
        self.assertEqual(message.status, "sent")
        self.assertEqual(message.email_sender, "test@example.com")


class TelegramIntegrationTestCase(TestCase):
    """Tests de integración con el sistema de emails"""

    def setUp(self):
        # Crear company
        self.company = Company.objects.create(name="Test Company", is_active=True)

        # Crear configuración de Telegram
        self.config = TelegramConfig.objects.create(
            name="Test Bot", bot_token="123456789:TEST_TOKEN", is_active=True
        )

        # Crear chat
        self.chat = TelegramChat.objects.create(
            name="Test Chat",
            chat_id=123456789,
            alert_level="all",
            email_alerts=True,
            is_active=True,
        )

    @patch("telegram_bot.tasks.send_email_alert_task.delay")
    def test_email_signal_triggers_telegram_alert(self, mock_task):
        """Test que la señal de email dispare una alerta de Telegram"""
        # Crear un email (esto debería disparar la señal)
        email = ReceivedEmail.objects.create(
            sender="test@example.com",
            subject="Test Email",
            body_text="This is a test email",
            body_html="<p>This is a test email</p>",
            priority="medium",
        )

        # Verificar que se llamó la tarea de Telegram
        mock_task.assert_called_once()

        # Verificar los argumentos
        call_args = mock_task.call_args
        self.assertEqual(call_args[1]["email_subject"], "Test Email")
        self.assertEqual(call_args[1]["email_sender"], "test@example.com")
        self.assertEqual(call_args[1]["email_priority"], "medium")
