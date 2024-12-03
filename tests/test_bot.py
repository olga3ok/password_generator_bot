import pytest
from bot import PasswordBot
from unittest.mock import AsyncMock, MagicMock
import asyncio


@pytest.fixture
def bot_instance():
    """Фикстура для создания экземпляра PasswordBot"""
    bot = PasswordBot()
    bot.redis = AsyncMock()
    return bot


def test_generate_password(bot_instance):
    """Тестирование генерации пароля"""
    password = bot_instance.generate_password(12)
    assert len(password) == 12
    assert isinstance(password, str)
    assert any(char.islower() for char in password)
    assert any(char.isupper() for char in password)
    assert any(char.isdigit() for char in password)
    assert any(not char.isalnum() for char in password)


@pytest.mark.asyncio
async def test_redis_connection(bot_instance):
    """Тестирование подключения к Redis"""
    bot_instance.redis.ping = AsyncMock(return_value=True)
    assert await bot_instance.redis.ping() is True


@pytest.mark.asyncio
async def test_start_command_with_saved_length(bot_instance):
    """Тестирование команды /start с сохраненной длиной пароля"""
    # Заглушка для ответа от Redis
    async def mock_get(key):
        if key == "user12345:password_length":
            return b"12"
        return None

    bot_instance.redis.get = mock_get

    class MockMessage:
        def __init__(self):
            self.text = "/start"
            self.from_user = type("User", (), {"id": 12345, "first_name": "TestUser"})
            self.reply_text = None

        async def reply(self, text, reply_markup=None):
            self.reply_text = text

    message = MockMessage()
    await bot_instance.start_command(message)

    assert "В прошлый раз вы использовали длину пароля 12 символов.\n"
    assert "Хотите сгенерировать новый пароль той же длины?"


@pytest.mark.asyncio
async def test_start_command_without_saved_length(bot_instance):
    """Тестирование команды /start без сохраненной длины пароля"""
    # Мок для Redis
    bot_instance.redis.get = AsyncMock(return_value=None)

    class MockMessage:
        def __init__(self):
            self.text = "/start"
            self.from_user =  type("User", (), {"id": 12345, "first_name": "TestUser"})
            self.reply_text = None

        async def reply(self, text, reply_markup=None):
            self.reply_text = text

    message = MockMessage()
    await bot_instance.start_command(message)

    assert "Привет! Я помогу сгенерировать пароль. Выбери длину пароля:"


def test_generate_password_too_short(bot_instance):
    """Тестирования генерации пароля с длиной менее 8 символов"""
    with pytest.raises(ValueError):
        bot_instance.generate_password(3)
