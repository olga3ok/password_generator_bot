import random
import aioredis
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils import executor
from config import TOKEN, REDIS_HOST, REDIS_PORT


class PasswordBot:
    def __init__(self, token=TOKEN):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(self.bot)
        self.redis_host = REDIS_HOST
        self.redis_port = REDIS_PORT
        self.redis = None
        self.keyboard = self._create_keyboard()

    async def init_redis(self):
        """Инициализация подключения к Redis"""
        self.redis = await aioredis.from_url(f"redis://{self.redis_host}:{self.redis_port}", decode_responses=True)

    @staticmethod
    def generate_password(length: int) -> str:
        """Генерация пароля"""
        if length < 8: # минимальная длина пароля
            raise ValueError("Длина пароля должна быть не менее 4 символов")

        lower = random.choice(string.ascii_lowercase)
        upper = random.choice(string.ascii_uppercase)
        digit = random.choice(string.digits)
        special = random.choice(string.punctuation)

        all_characters = string.ascii_letters + string.digits + string.punctuation
        remaining = [random.choice(all_characters) for _ in range(length - 4)]

        password = list(lower + upper + digit + special + ''.join(remaining))
        random.shuffle(password)

        return ''.join(password)

    @staticmethod
    def _create_keyboard():
        """Создание клавиатуры для выбора длины пароля"""
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(
            KeyboardButton("8 символов"),
            KeyboardButton("12 символов"),
            KeyboardButton("16 символов"),
            KeyboardButton("Своя длина"),
        )
        return keyboard

    async def start_command(self, message: types.Message):
        """Обработка команды /start """
        user_id = message.from_user.id
        saved_length = await self.redis.get(f"user:{user_id}:password_length")
        if saved_length:
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("Подтвердить", callback_data=f"confirm_length:{saved_length}"),
                InlineKeyboardButton("Выбрать другую длину", callback_data="choose_new_length")
            )
            await message.reply(
                f"Привет, {message.from_user.first_name}! "
                f"В прошлый раз вы использовали длину пароля {saved_length} символов.\n"
                "Хотите сгенерировать новый пароль той же длины?",
                reply_markup=keyboard
            )
        else:
            await message.reply(
                "Привет! Я помогу сгенерировать пароль. Выбери длину пароля:"
            )

    async def predefined_length(self, message: types.Message):
        """Обработка предустановленной длины пароля"""
        user_id = message.from_user.id
        length = int(message.text.split()[0])
        await self.redis.set(f"user:{user_id}:password_length", length)
        password = self.generate_password(length)
        await message.reply(f"Вот твой пароль:\n```\n{password}\n```", parse_mode="Markdown")

    async def custom_length_request(self, message: types.Message):
        """Обработка запроса на кастомную длину пароля"""
        await message.reply("Введите желаемую длину пароля ( от 8 до 64):")

    async def custom_length_response(self, message: types.Message):
        """Обработка кастомной длины пароля"""
        user_id = message.from_user.id
        try:
            length = int(message.text)
            if 8 <= length <= 64:
                await self.redis.set(f"user:{user_id}:password_length", length)
                password = self.generate_password(length)
                await message.reply(f"Вот твой пароль: \n```\n{password}\n```", parse_mode="Markdown")
            else:
                await message.reply("Укажите длину в диапазоне от 8 до 64.")
        except ValueError:
            await message.reply("Пожалуйста, укажите длину пароля числом")

    async def handle_confirm_length(self, callback_query: CallbackQuery):
        """Обработчик подтверждения длины пароля"""
        user_id = callback_query.from_user.id
        data = callback_query.data
        length = int(data.split(":")[1])

        password = self.generate_password(length)
        await callback_query.message.edit_text(
            f"Вот твой пароль: \n```\n{password}\n```", parse_mode="Markdown"
        )

    async def handle_choose_new_length(self, callback_query: CallbackQuery):
        """Обработчик выбора новой длины пароля"""
        await callback_query.message.edit_text("Выберите новую длину пароля: ")

    async def handle_invalid_message(self, message: types.Message):
        """Обработка некорректных сообщений"""
        await message.reply("Пожалуйста, выберите длину пароля из меню или введите число.")

    def register_handlers(self):
        """Регистрация обработчиков сообщений"""
        self.dp.register_message_handler(self.start_command, commands=["start"])
        self.dp.register_callback_query_handler(self.handle_confirm_length, lambda c: c.data.startswith("confirm_length"))
        self.dp.register_callback_query_handler(self.handle_choose_new_length, lambda c: c.data == "choose_new_length")
        self.dp.register_message_handler(self.predefined_length, lambda msg: msg.text in ["8 символов", "12 символов", "16 символов"])
        self.dp.register_message_handler(self.custom_length_request, lambda msg: msg.text == "Своя длина")
        self.dp.register_message_handler(self.custom_length_response, lambda msg: msg.text.isdigit())
        self.dp.register_message_handler(self.handle_invalid_message)

    def run(self):
        """Запуск бота"""
        executor.start_polling(self.dp, skip_updates=True)


if __name__ == "__main__":
    import asyncio

    bot = PasswordBot(TOKEN)

    loop = asyncio.new_event_loop() # Явно создаем новый цикл событий
    asyncio.set_event_loop(loop) # Назначаем его текущим
    loop.run_until_complete(bot.init_redis()) # Запускаем асинхронную инициализацию Redis

    bot.register_handlers()
    bot.run()
