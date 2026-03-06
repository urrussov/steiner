from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters
)

import sqlite3

TOKEN = "8394944761:AAEJRePpx4FLQvXZuBtTXtrAyoDzdap2Tmk"


from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters
)

import sqlite3

TOKEN = "8394944761:AAEJRePpx4FLQvXZuBtTXtrAyoDzdap2Tmk"


NAME, ROLE = range(2)

PROCESS_NUMBER, CLIENT_NAME, COMPANY_NAME, POLAND, PROCESS_DESCRIPTION, SUPPLIER, SUPPLIER_MENU = range(7)

role_map = {
    "Адміністратор": "admin",
    "Менеджер": "manager",
    "Бухгалтер": "accountant"
}

# ---------------- DATABASE ----------------

def get_connection():
    conn = sqlite3.connect("DATABASE.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def add_user(name, role, telegram_id):

    conn = get_connection()

    with conn:
        conn.execute(
            "INSERT INTO users (name, role, telegram_id) VALUES (?, ?, ?)",
            (name, role, telegram_id)
        )

    conn.close()


def check_user(telegram_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, role FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )

    user = cursor.fetchone()

    conn.close()

    return user


def add_process(process_number, client_name, company_name, description, telegram_id, poland):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )
    user_id = cursor.fetchone()[0]

    cursor.execute(
        "SELECT id FROM companies WHERE name = ?",
        (company_name,)
    )
    company = cursor.fetchone()

    if not company:
        raise Exception("Компанія не знайдена")

    origin_company_id = company[0]

    with conn:
        conn.execute(
            """
            INSERT INTO processes (
                process_number,
                client_name,
                origin_company_id,
                steiner_poland_involved,
                description,
                start_date,
                status,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, DATE('now'), 'open', ?)
            """,
            (
                process_number,
                client_name,
                origin_company_id,
                poland,
                description,
                user_id
            )
        )

    conn.close()


def get_process_id(process_number):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM processes WHERE process_number = ?",
        (process_number,)
    )

    process_id = cursor.fetchone()[0]

    conn.close()

    return process_id


def add_supplier(process_id, supplier_name):

    conn = get_connection()

    with conn:
        conn.execute(
            "INSERT INTO suppliers (process_id, supplier_name) VALUES (?, ?)",
            (process_id, supplier_name)
        )

    conn.close()


# ---------------- MESSAGE TRACKING ----------------

def save_user_message(update, context):

    if "dialog_messages" not in context.user_data:
        context.user_data["dialog_messages"] = []

    context.user_data["dialog_messages"].append(update.message.message_id)


async def send_message(update, context, text, reply_markup=None, remove_keyboard=False):

    if remove_keyboard:
        reply_markup = ReplyKeyboardRemove()

    msg = await update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    if "dialog_messages" not in context.user_data:
        context.user_data["dialog_messages"] = []

    context.user_data["dialog_messages"].append(msg.message_id)

    return msg


async def clear_dialog(update, context):

    chat_id = update.effective_chat.id

    for msg_id in context.user_data.get("dialog_messages", []):
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except:
            pass

    context.user_data["dialog_messages"] = []


# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.effective_user.id

    user = check_user(telegram_id)

    if not user:

        keyboard = [["Зареєструватися"]]

        await update.message.reply_text(
            "Привіт! Ви не зареєстровані.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    else:
        await show_main_menu(update)


async def show_main_menu(update: Update):

    keyboard = [
        ["Додати процес", "Додати інвойс"],
        ["Додати оплату", "Пошук"],
        ["Історія процесу"]
    ]

    await update.message.reply_text(
        "Оберіть дію:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ---------------- REGISTER ----------------

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    await send_message(
        update,
        context,
        "Введіть ваше ім'я та прізвище:",
        remove_keyboard=True
    )

    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["name"] = update.message.text

    keyboard = [
        ["Адміністратор"],
        ["Менеджер"],
        ["Бухгалтер"]
    ]

    await send_message(
        update,
        context,
        "Оберіть вашу роль:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return ROLE


async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    role = role_map.get(update.message.text)

    name = context.user_data["name"]

    telegram_id = update.effective_user.id

    try:

        add_user(name, role, telegram_id)

        await clear_dialog(update, context)

        await update.message.reply_text(
            f"Користувач {name} зареєстрований",
            reply_markup=ReplyKeyboardRemove()
        )

        await show_main_menu(update)

    except Exception as e:

        await update.message.reply_text(f"Помилка: {e}")

    return ConversationHandler.END


# ---------------- PROCESS ----------------

async def start_add_process(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    await send_message(
        update,
        context,
        "Введіть номер процесу:",
        remove_keyboard=True
    )

    return PROCESS_NUMBER


async def get_process_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    process_number = update.message.text.strip().lstrip("#")

    context.user_data["process_number"] = process_number

    await send_message(update, context, "Введіть назву клієнта:")

    return CLIENT_NAME


async def get_client(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["client_name"] = update.message.text

    keyboard = [
        ["LLC Steiner Ukraine"],
        ["Steiner Polska sp. z o.o."],
        ["LLC Spels"],
        ["Spels MEA"]
    ]

    await send_message(
        update,
        context,
        "Оберіть компанію яка веде процес:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return COMPANY_NAME

async def get_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["company_name"] = update.message.text

    keyboard = [
        ["Так"],
        ["Ні"]
    ]

    await send_message(
        update,
        context,
        "Чи буде Steiner Polska sp. z o.o. також брати участь у цьому процесі?",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return POLAND

async def get_poland(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    answer = update.message.text

    if answer == "Так":
        context.user_data["poland"] = 1
    else:
        context.user_data["poland"] = 0

    await send_message(
        update,
        context,
        "Опишіть процес:",
        remove_keyboard=True
    )

    return PROCESS_DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["description"] = update.message.text

    context.user_data["suppliers"] = []

    await send_message(update, context, "Введіть постачальника:")

    return SUPPLIER


async def get_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    supplier = update.message.text

    context.user_data["suppliers"].append(supplier)

    keyboard = [["Додати ще"], ["Готово"]]

    await send_message(
        update,
        context,
        "Постачальника додано",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return SUPPLIER_MENU


async def supplier_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    choice = update.message.text

    if choice == "Додати ще":

        await send_message(
            update,
            context,
            "Введіть постачальника:",
            remove_keyboard=True
        )

        return SUPPLIER

    if choice == "Готово":

        process_number = context.user_data["process_number"]
        client_name = context.user_data["client_name"]
        company_name = context.user_data["company_name"]
        description = context.user_data["description"]
        suppliers = context.user_data.get("suppliers", [])
        poland = context.user_data["poland"]
        telegram_id = update.effective_user.id

        add_process(
            process_number,
            client_name,
            company_name,
            description,
            telegram_id,
            poland
        )

        process_id = get_process_id(process_number)

        for supplier in suppliers:
            add_supplier(process_id, supplier)

        await clear_dialog(update, context)

        supplier_list = "\n".join([f"• {s}" for s in suppliers]) if suppliers else "—"

        poland_text = "✅" if poland else "❌"

        await update.message.reply_text(
            f"""
📦 *Процес #{process_number}*

Клієнт: *{client_name}*
Компанія: *{company_name}*
Steiner Polska: *{poland_text}*

Постачальники:
{supplier_list}

Статус: `open`

Опис:
{description}
""",
            parse_mode="Markdown"
        )

        await show_main_menu(update)

        return ConversationHandler.END


# ---------------- BOT ----------------

app = ApplicationBuilder().token(TOKEN).build()

register_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Зареєструватися$"), register)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
    },
    fallbacks=[]
)

process_conversation = ConversationHandler(

    entry_points=[
        MessageHandler(filters.Regex("^Додати процес$"), start_add_process)
    ],

    states={

        PROCESS_NUMBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_process_number)
        ],

        CLIENT_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_client)
        ],

        COMPANY_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_company_name)
        ],

        POLAND: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_poland)
        ],

        PROCESS_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)
        ],

        SUPPLIER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_supplier)
        ],

        SUPPLIER_MENU: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, supplier_menu)
        ],

    },

    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(register_conversation)
app.add_handler(process_conversation)

app.run_polling()