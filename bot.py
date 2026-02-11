import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from dotenv import load_dotenv

#настройки
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Файл .env загружен из: {env_path}")
else:
    load_dotenv()  # Попытка загрузить из текущей директории
    logger.info("Попытка загрузить .env из текущей директории")

# Токен бота и ID администраторов
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS_STR = os.getenv('ADMIN_ID', '')

# Отладочная информация
logger.info(f"BOT_TOKEN найден: {'Да' if BOT_TOKEN else 'Нет'}")
logger.info(f"ADMIN_ID найден: {'Да' if ADMIN_IDS_STR else 'Нет'}")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения! Проверьте файл .env")

if not ADMIN_IDS_STR:
    raise ValueError("ADMIN_ID не найден в переменных окружения! Проверьте файл .env")

# Парсим список администраторов (можно указать через запятую или один ID)
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()]
if not ADMIN_IDS:
    raise ValueError("Не удалось распарсить ADMIN_ID! Укажите хотя бы один ID администратора")

logger.info(f"Загружено администраторов: {len(ADMIN_IDS)}")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище связей между сообщениями администратора и пользователями
# Ключ: (admin_chat_id, message_id) - кортеж из ID чата администратора и ID сообщения
# Значение: user_id пользователя
user_messages_map = {}

# Состояния пользователя
class UserState(StatesGroup):
    waiting_for_message = State()


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    welcome_text = (
        "💬 Доброго дня!\n\n"
        "Дякуємо за ваше звернення 💛\n\n"
        "Будь ласка, напишіть своє запитання — оператор відповість вам найближчим часом"
    )
    
    await message.answer(welcome_text)
    await state.set_state(UserState.waiting_for_message)
    # Устанавливаем флаг, что подтверждение еще не отправлялось
    await state.update_data(first_message_sent=False)
    logger.info(f"Пользователь {message.from_user.id} ({message.from_user.username}) начал диалог")


@dp.message(lambda message: message.from_user.id in ADMIN_IDS)
async def handle_admin_message(message: Message):
    """Обработка сообщений от администратора"""
    # Проверяем, что это администратор
    if message.from_user.id not in ADMIN_IDS:
        return
    
    admin_chat_id = message.chat.id
    
    # Если это ответ на сообщение (reply)
    if message.reply_to_message:
        # Получаем сообщение, на которое ответили
        replied_message = message.reply_to_message
        replied_message_id = replied_message.message_id
        
        # Ищем user_id в нашем словаре по ключу (admin_chat_id, message_id)
        # Также проверяем общий ключ message_id на случай, если сообщение было отправлено в личку
        user_id = user_messages_map.get((admin_chat_id, replied_message_id))
        if user_id is None:
            # Пробуем найти по message_id (для обратной совместимости)
            user_id = user_messages_map.get(replied_message_id)
        
        # Если не нашли, значит это не наше сообщение
        if user_id is None:
            return
        
        # Отправляем ответ пользователю от имени бота
        try:
            # Обрабатываем разные типы сообщений
            if message.photo:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption
                )
                logger.info(f"Фото от администратора отправлено пользователю {user_id}")
            elif message.document:
                await bot.send_document(
                    chat_id=user_id,
                    document=message.document.file_id,
                    caption=message.caption
                )
                logger.info(f"Документ от администратора отправлен пользователю {user_id}")
            elif message.video:
                await bot.send_video(
                    chat_id=user_id,
                    video=message.video.file_id,
                    caption=message.caption
                )
                logger.info(f"Видео от администратора отправлено пользователю {user_id}")
            elif message.audio:
                await bot.send_audio(
                    chat_id=user_id,
                    audio=message.audio.file_id,
                    caption=message.caption
                )
                logger.info(f"Аудио от администратора отправлено пользователю {user_id}")
            elif message.voice:
                await bot.send_voice(
                    chat_id=user_id,
                    voice=message.voice.file_id,
                    caption=message.caption
                )
                logger.info(f"Голосовое сообщение от администратора отправлено пользователю {user_id}")
            elif message.video_note:
                await bot.send_video_note(
                    chat_id=user_id,
                    video_note=message.video_note.file_id
                )
                logger.info(f"Кружок от администратора отправлен пользователю {user_id}")
            elif message.sticker:
                await bot.send_sticker(
                    chat_id=user_id,
                    sticker=message.sticker.file_id
                )
                logger.info(f"Стикер от администратора отправлен пользователю {user_id}")
            else:
                # Текстовое сообщение
                reply_text = message.text or message.caption or "Ответ администратора"
                await bot.send_message(
                    chat_id=user_id,
                    text=reply_text
                )
                logger.info(f"Текстовое сообщение от администратора отправлено пользователю {user_id}")
            
            # Подтверждение администратору
            await message.answer("✅ Ответ отправлен пользователю")
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа пользователю: {e}")
            await message.answer(f"❌ Ошибка при отправке сообщения: {e}")


@dp.message(StateFilter(UserState.waiting_for_message))
async def handle_user_message(message: Message, state: FSMContext):
    """Обработка сообщений от пользователей"""
    # Пропускаем сообщения администратора
    if message.from_user.id in ADMIN_IDS:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # Получаем данные состояния
    data = await state.get_data()
    first_message_sent = data.get('first_message_sent', False)
    
    # Отправляем подтверждение только после первого сообщения
    if not first_message_sent:
        confirmation_text = (
            "✨ Ваше повідомлення отримали!\n\n"
            "Наша команда вже переглядає його — і дуже скоро ви отримаєте відповідь 🤍"
        )
        await message.answer(confirmation_text)
        # Устанавливаем флаг, что подтверждение уже отправлено
        await state.update_data(first_message_sent=True)
    
    # Отправляем сообщение всем администраторам от имени бота (копируем контент)
    try:
        # Формируем заголовок с информацией о пользователе
        # Всегда добавляем заголовок, чтобы было видно от кого сообщение
        current_time = datetime.now().strftime("%H:%M")
        if not first_message_sent:
            # Для первого сообщения - полный заголовок с разделителем
            header = f"👤 {first_name} {last_name} (@{username}) | {current_time}\n" + "─" * 30 + "\n\n"
        else:
            # Для последующих сообщений - компактный заголовок
            header = f"👤 {first_name} {last_name} (@{username}) | {current_time}\n\n"
        
        # Отправляем сообщение всем администраторам
        # Каждое сообщение обрабатывается независимо, aiogram обрабатывает их асинхронно
        for admin_id in ADMIN_IDS:
            try:
                admin_message = None
                
                if message.photo:
                    # Отправляем фото с подписью
                    caption = header + (message.caption or "")
                    admin_message = await bot.send_photo(
                        chat_id=admin_id,
                        photo=message.photo[-1].file_id,
                        caption=caption[:1024] if len(caption) > 1024 else caption
                    )
                elif message.document:
                    caption = header + (message.caption or "")
                    admin_message = await bot.send_document(
                        chat_id=admin_id,
                        document=message.document.file_id,
                        caption=caption[:1024] if len(caption) > 1024 else caption
                    )
                elif message.video:
                    caption = header + (message.caption or "")
                    admin_message = await bot.send_video(
                        chat_id=admin_id,
                        video=message.video.file_id,
                        caption=caption[:1024] if len(caption) > 1024 else caption
                    )
                elif message.audio:
                    caption = header + (message.caption or "")
                    admin_message = await bot.send_audio(
                        chat_id=admin_id,
                        audio=message.audio.file_id,
                        caption=caption[:1024] if len(caption) > 1024 else caption
                    )
                elif message.voice:
                    caption = header + (message.caption or "")
                    admin_message = await bot.send_voice(
                        chat_id=admin_id,
                        voice=message.voice.file_id,
                        caption=caption[:200] if len(caption) > 200 else caption
                    )
                elif message.video_note:
                    # Для video_note отправляем информацию о пользователе перед каждым сообщением
                    info_msg = await bot.send_message(
                        chat_id=admin_id,
                        text=header.strip()
                    )
                    user_messages_map[(admin_id, info_msg.message_id)] = user_id
                    admin_message = await bot.send_video_note(
                        chat_id=admin_id,
                        video_note=message.video_note.file_id
                    )
                elif message.sticker:
                    # Для стикера отправляем информацию о пользователе перед каждым сообщением
                    info_msg = await bot.send_message(
                        chat_id=admin_id,
                        text=header.strip()
                    )
                    user_messages_map[(admin_id, info_msg.message_id)] = user_id
                    admin_message = await bot.send_sticker(
                        chat_id=admin_id,
                        sticker=message.sticker.file_id
                    )
                else:
                    # Текстовое сообщение
                    text = header + (message.text or message.caption or "")
                    admin_message = await bot.send_message(
                        chat_id=admin_id,
                        text=text
                    )
                
                # Сохраняем связь между сообщением администратора и пользователем
                if admin_message:
                    user_messages_map[(admin_id, admin_message.message_id)] = user_id
                    # Также сохраняем по старому ключу для обратной совместимости
                    user_messages_map[admin_message.message_id] = user_id
                
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения администратору {admin_id}: {e}")
        
        logger.info(f"Сообщение от пользователя {user_id} ({first_name} @{username}) отправлено всем администраторам")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения администраторам: {e}")
        await message.answer("❌ Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.")


@dp.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """Обработка сообщений от пользователей, которые еще не начали диалог"""
    # Пропускаем сообщения администратора
    if message.from_user.id in ADMIN_IDS:
        return
    
    # Пользователь еще не начал диалог
    await message.answer(
        "👋 Привіт! Для початку роботи надішліть команду /start"
    )


async def main():
    """Основная функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Удаляем вебхук и опрашиваем сервер
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")


