import asyncio
import json
import os
import random
import sys
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    WebAppInfo,
)

# Принудительный UTF-8 для консоли
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()
BOT_TOKEN = config.get("bot_token")
ADMIN_ID = config.get("admin_id")
WEBAPP_URL = config.get("webapp_url", "https://qavalerq.github.io/cyberdine/")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Открыть меню CyberDine",
                    web_app=WebAppInfo(url=url)
                )
            ],
            [
                InlineKeyboardButton(text="📍 Локация и часы", callback_data="info_location"),
                InlineKeyboardButton(text="💬 Поддержка", callback_data="info_support")
            ]
        ]
    )

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name

    # Настраиваем постоянную кнопку меню в левом нижнем углу Телеграма
    try:
        await bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(
                text="Меню 🍔",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
    except Exception as e:
        print(f"[!] Не удалось установить MenuButton: {e}")

    welcome_text = (
        f"⚡ <b>Добро пожаловать в CyberDine, {user_name}!</b>\n\n"
        f"Футуристичный стритфуд и крафтовый кофе в Новороссийске.\n\n"
        f"• Трюфельные бургеры на бриоши\n"
        f"• Азотный Nitro Cold Brew\n"
        f"• Баскские чизкейки\n\n"
        f"Нажмите кнопку ниже, чтобы открыть интерактивное приложение и собрать заказ:"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_keyboard(WEBAPP_URL),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "info_location")
async def cb_location(callback: types.CallbackQuery):
    await callback.message.answer(
        "📍 <b>CyberDine Hub:</b>\nг. Новороссийск, Набережная им. Адмирала Серебрякова\n\n"
        "🕒 <b>Часы работы:</b> ежедневно с 10:00 до 23:00\n"
        "🚀 <b>Доставка:</b> от 25 минут",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data == "info_support")
async def cb_support(callback: types.CallbackQuery):
    await callback.message.answer(
        "💬 <b>Служба заботы CyberDine:</b>\n"
        "По всем вопросам заказа пишите менеджеру: @qavalerdsg",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ОБРАБОТЧИК ЗАКАЗА ИЗ TELEGRAM MINI APP
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    raw_data = message.web_app_data.data
    order_id = f"CD-{random.randint(1000, 9999)}"
    now_time = datetime.now().strftime("%H:%M")

    try:
        data = json.loads(raw_data)
        items = data.get("items", [])
        total = data.get("total", 0)
        customer = data.get("user", message.from_user.first_name)
    except Exception:
        items = [raw_data]
        total = "По чеку"
        customer = message.from_user.first_name

    items_list_str = "\n".join([f"  • {item}" for item in items])

    # 1. Чек клиенту
    client_receipt = (
        f"🎉 <b>ЗАКАЗ #{order_id} УСПЕШНО ОФОРМЛЕН!</b>\n\n"
        f"👤 <b>Клиент:</b> {customer}\n"
        f"⏱ <b>Время заказа:</b> {now_time}\n"
        f"⏳ <b>Готовность:</b> ~20–25 минут\n\n"
        f"📋 <b>Состав заказа:</b>\n"
        f"{items_list_str}\n\n"
        f"💳 <b>Итого к оплате:</b> <b>{total} ₽</b>\n\n"
        f"<i>Шеф уже начал готовить ваш заказ! Мы уведомим вас о готовности.</i>"
    )

    await message.answer(client_receipt, parse_mode=ParseMode.HTML)

    # 2. Уведомление администратору/кухне
    if ADMIN_ID:
        admin_alert = (
            f"🔔 <b>НОВЫЙ ЗАКАЗ #{order_id}!</b>\n\n"
            f"👤 <b>Покупатель:</b> @{message.from_user.username or 'без юзернейма'} ({customer})\n"
            f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n\n"
            f"📋 <b>Позиции:</b>\n"
            f"{items_list_str}\n\n"
            f"💰 <b>Сумма:</b> <b>{total} ₽</b>"
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[!] Не удалось отправить уведомление админу: {e}")

async def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()

    async def handle_ping(request):
        return web.Response(text="CyberDine Bot is running!")

    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[*] Web Health-Check запущен на порту {port}")

async def main():
    me = await bot.get_me()
    print("=" * 60)
    print(f" 🍔 CyberDine Telegram Bot запущен: @{me.username} ({me.first_name})")
    print(f" WebApp URL: {WEBAPP_URL}")
    print(" Ожидаю команды и заказы от пользователей...")
    print("=" * 60)

    try:
        await start_web_server()
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nCyberDine Bot остановлен.")
