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


# REGISTER
NAME, ROLE = range(2)

# PROCESS
PROCESS_NUMBER, CLIENT_NAME, COMPANY_NAME, POLAND, PROCESS_DESCRIPTION, SUPPLIER, SUPPLIER_MENU = range(10,17)

# INVOICE
INVOICE_CLIENT, INVOICE_PROCESS, INVOICE_TYPE, INVOICE_NUMBER, INVOICE_DATE, INVOICE_SELLER, INVOICE_BUYER, INVOICE_AMOUNT, INVOICE_CURRENCY, INVOICE_RATE = range(20,30)

#PAYMENTS
PAYMENT_CLIENT, PAYMENT_PROCESS, PAYMENT_INVOICE, PAYMENT_NUMBER, PAYMENT_AMOUNT, PAYMENT_CURRENCY, PAYMENT_RATE, PAYMENT_DATE = range(40,48)

# HISTORY
HISTORY_CLIENT, HISTORY_PROCESS = range(50,52)

role_map = {
    "Адміністратор": "admin",
    "Менеджер": "manager",
    "Бухгалтер": "accountant"
}
CANCEL = "❌ Закрити"

# ---------------- DATABASE ----------------

def get_connection():

    conn = sqlite3.connect("DATABASE.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def add_user(name, role, telegram_id):

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (name, role, telegram_id)
                VALUES (?, ?, ?)
                """,
                (name, role, telegram_id)
            )
    finally:
        conn.close()


def check_user(telegram_id):

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, role
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def add_process(process_number, client_name, company_name, description, telegram_id, poland):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise Exception("User not found")

        user_id = user["id"]

        # -------- CLIENT ENTITY --------

        cursor.execute(
            """
            INSERT OR IGNORE INTO entities (name, type)
            VALUES (?, 'client')
            """,
            (client_name,)
        )

        cursor.execute(
            "SELECT id FROM entities WHERE name = ?",
            (client_name,)
        )

        client_id = cursor.fetchone()["id"]

        # -------- COMPANY ENTITY --------

        cursor.execute(
            """
            SELECT id
            FROM entities
            WHERE name = ?
            AND type = 'company'
            """,
            (company_name,)
        )

        company = cursor.fetchone()

        if not company:
            raise Exception("Компанія не знайдена")

        company_id = company["id"]

        # -------- INSERT PROCESS --------

        with conn:

            conn.execute(
                """
                INSERT INTO processes (
                    process_number,
                    client_entity_id,
                    managing_company_id,
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
                    client_id,
                    company_id,
                    poland,
                    description,
                    user_id
                )
            )

        process_id = get_process_id(process_number)

        add_event(
            conn,
            process_id,
            user_id,
            "process_created",
            f"Створено процес #{process_number}"
        )

        # -------- PARTICIPANTS --------

        with conn:

            conn.execute(
                """
                INSERT OR IGNORE INTO process_participants
                (process_id, entity_id, role)
                VALUES (?, ?, 'client')
                """,
                (process_id, client_id)
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO process_participants
                (process_id, entity_id, role)
                VALUES (?, ?, 'company')
                """,
                (process_id, company_id)
            )

    finally:
        conn.close()

def get_process_id(process_number):

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM processes
            WHERE process_number = ?
            """,
            (process_number,)
        )
        row = cursor.fetchone()

        if not row:
            raise Exception("Процес не знайдений")
        return row["id"]
    finally:
        conn.close()

def add_supplier(process_id, supplier_name):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO entities (name, type)
            VALUES (?, 'supplier')
            """,
            (supplier_name,)
        )

        cursor.execute(
            "SELECT id FROM entities WHERE name = ?",
            (supplier_name,)
        )

        supplier_id = cursor.fetchone()["id"]

        with conn:

            conn.execute(
                """
                INSERT OR IGNORE INTO process_participants
                (process_id, entity_id, role)
                VALUES (?, ?, 'supplier')
                """,
                (process_id, supplier_id)
            )

    finally:
        conn.close()

# -------- INVOICE DATABASE --------

def get_clients():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name
            FROM entities
            WHERE type='client'
            ORDER BY name
            """
        )

        return cursor.fetchall()

    finally:
        conn.close()

def get_companies():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name
            FROM entities
            WHERE type='company'
            ORDER BY name
            """
        )

        return cursor.fetchall()

    finally:
        conn.close()

def get_processes_by_client(client_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, process_number
            FROM processes
            WHERE client_entity_id = ?
            ORDER BY process_number DESC
            """,
            (client_id,)
        )

        return cursor.fetchall()

    finally:
        conn.close()

def get_company_id(name):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id
            FROM entities
            WHERE name = ?
            AND type = 'company'
            """,
            (name,)
        )

        row = cursor.fetchone()

        if not row:
            raise Exception("Компанія не знайдена")

        return row["id"]

    finally:
        conn.close()

def add_invoice(data):

    conn = get_connection()

    try:

        amount = data["amount"]
        rate = data["exchange_rate_to_eur"]

        amount_eur = amount * rate

        with conn:

            cursor = conn.execute(
                """
                INSERT INTO invoices (
                    invoice_number,
                    process_id,
                    seller_entity_id,
                    buyer_entity_id,
                    invoice_type,
                    invoice_date,
                    amount,
                    currency,
                    exchange_rate_to_eur,
                    amount_eur
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["invoice_number"],
                    data["process_id"],
                    data["seller_company_id"],
                    data["buyer_company_id"],
                    data["invoice_type"],
                    data["invoice_date"],
                    amount,
                    data["currency"],
                    rate,
                    amount_eur
                )
            )

            invoice_id = cursor.lastrowid
            add_event(
                conn,
                data["process_id"],
                None,
                "invoice_created",
                f"Створено інвойс {data['invoice_number']} ({amount_eur:.2f} EUR)"
            )
            # ledger entry
            conn.execute(
                """
                INSERT INTO ledger
                (process_id, entity_from_id, entity_to_id, amount_eur, entry_type, reference_id)
                VALUES (?, ?, ?, ?, 'invoice', ?)
                """,
                (
                    data["process_id"],
                    data["seller_company_id"],
                    data["buyer_company_id"],
                    amount_eur,
                    invoice_id
                )
            )

    finally:
        conn.close()

def get_process_participants(process_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT e.id, e.name, e.type
            FROM process_participants pp
            JOIN entities e ON e.id = pp.entity_id
            WHERE pp.process_id = ?

            UNION

            SELECT id, name, type
            FROM entities
            WHERE type = 'company'

            ORDER BY name
            """,
            (process_id,)
        )

        return cursor.fetchall()

    finally:
        conn.close()

def get_process_number_db(process_id):

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT process_number
            FROM processes
            WHERE id = ?
            """,
            (process_id,)
        )

        row = cursor.fetchone()

        if row:
            return row["process_number"]

        return "—"

    finally:
        conn.close()

def set_poland_involved(process_id):

    conn = get_connection()

    try:

        with conn:

            conn.execute(
                """
                UPDATE processes
                SET steiner_poland_involved = 1
                WHERE id = ?
                """,
                (process_id,)
            )

    finally:
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await clear_dialog(update, context)

    await update.message.reply_text(
        "Операцію скасовано",
        reply_markup=ReplyKeyboardRemove()
    )

    await show_main_menu(update)

    return ConversationHandler.END


#----------------PAYMENTS DATABASE -----------------

def add_payment(data):

    conn = get_connection()

    try:

        amount = data["amount"]
        rate = data["exchange_rate_to_eur"]

        amount_eur = amount * rate

        with conn:

            cursor = conn.execute(
                """
                INSERT INTO payments (
                    payment_number,
                    process_id,
                    invoice_id,
                    from_entity_id,
                    to_entity_id,
                    amount,
                    currency,
                    payment_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["payment_number"],
                    data["process_id"],
                    data["invoice_id"],
                    data["from_entity_id"],
                    data["to_entity_id"],
                    amount,
                    data["currency"],
                    data["payment_date"]
                )
            )

            payment_id = cursor.lastrowid

            # ledger entry
            conn.execute(
                """
                INSERT INTO ledger
                (process_id, entity_from_id, entity_to_id, amount_eur, entry_type, reference_id)
                VALUES (?, ?, ?, ?, 'payment', ?)
                """,
                (
                    data["process_id"],
                    data["from_entity_id"],
                    data["to_entity_id"],
                    amount_eur,
                    payment_id
                )
            )
            add_event(
                conn,
                data["process_id"],
                None,
                "payment_added",
                f"Додано платіж {data['payment_number']} ({amount_eur:.2f} EUR)"
            )

    finally:
        conn.close()

def get_process_balance(process_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                entity_from_id,
                entity_to_id,
                SUM(amount_eur) as total
            FROM ledger
            WHERE process_id = ?
            GROUP BY entity_from_id, entity_to_id
            """,
            (process_id,)
        )

        return cursor.fetchall()

    finally:
        conn.close()

def get_process_finance(process_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # клієнтські інвойси
        cursor.execute(
            """
            SELECT SUM(amount_eur)
            FROM invoices
            WHERE process_id = ?
            """,
            (process_id,)
        )

        invoices = cursor.fetchone()[0] or 0

        # платежі
        cursor.execute(
            """
            SELECT SUM(amount * exchange_rate_to_eur)
            FROM payments
            WHERE process_id = ?
            """,
            (process_id,)
        )

        payments = cursor.fetchone()[0] or 0

        return invoices, payments

    finally:
        conn.close()

def get_process_invoices(process_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, invoice_number, amount, currency
            FROM invoices
            WHERE process_id = ?
            ORDER BY invoice_date DESC
            """,
            (process_id,)
        )

        return cursor.fetchall()

    finally:
        conn.close()

def get_invoice(invoice_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                seller_entity_id,
                buyer_entity_id,
                amount,
                currency
            FROM invoices
            WHERE id = ?
            """,
            (invoice_id,)
        )

        return cursor.fetchone()

    finally:
        conn.close()

def update_invoice_status(invoice_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # сума інвойсу
        cursor.execute(
            """
            SELECT amount_eur
            FROM invoices
            WHERE id = ?
            """,
            (invoice_id,)
        )

        row = cursor.fetchone()

        if not row:
            return

        invoice_amount = row["amount_eur"]

        # сума оплат
        cursor.execute(
            """
            SELECT SUM(amount * COALESCE(exchange_rate_to_eur,1)) AS paid
            FROM payments
            WHERE invoice_id = ?
            """,
            (invoice_id,)
        )

        paid = cursor.fetchone()["paid"] or 0

        # визначаємо статус
        if paid == 0:

            status = "issued"

        elif paid < invoice_amount:

            status = "partially_paid"

        else:

            status = "paid"

        with conn:

            conn.execute(
                """
                UPDATE invoices
                SET status = ?
                WHERE id = ?
                """,
                (status, invoice_id)
            )

    finally:
        conn.close()

def get_invoice_payment_status(invoice_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT amount_eur, invoice_number
            FROM invoices
            WHERE id = ?
            """,
            (invoice_id,)
        )

        invoice = cursor.fetchone()

        if not invoice:
            return None

        invoice_amount = invoice["amount_eur"]
        invoice_number = invoice["invoice_number"]

        cursor.execute(
            """
            SELECT SUM(amount * COALESCE(exchange_rate_to_eur,1)) as paid
            FROM payments
            WHERE invoice_id = ?
            """,
            (invoice_id,)
        )

        paid = cursor.fetchone()["paid"] or 0

        remaining = invoice_amount - paid

        return {
            "invoice_number": invoice_number,
            "invoice_amount": invoice_amount,
            "paid": paid,
            "remaining": remaining
        }

    finally:
        conn.close()

#----------- HISTORY DATABASE -----------

def add_event(conn, process_id, user_id, event_type, description):

    conn.execute(
        """
        INSERT INTO events (
            process_id,
            user_id,
            event_type,
            description
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            process_id,
            user_id,
            event_type,
            description
        )
    )

def get_process_events(process_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT created_at, description
            FROM events
            WHERE process_id = ?
            ORDER BY created_at DESC
            """,
            (process_id,)
        )

        return cursor.fetchall()

    finally:
        conn.close()

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

    keyboard = [[CANCEL]]

    await send_message(
        update,
        context,
        "Введіть номер процесу:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return PROCESS_NUMBER

async def get_process_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    process_number = update.message.text.strip().lstrip("#")

    context.user_data["process_number"] = process_number

    keyboard = [[CANCEL]]

    await send_message(
        update,
        context,
        "Введіть назву клієнта:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CLIENT_NAME

async def get_client(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["client_name"] = update.message.text

    keyboard = [
        ["LLC Steiner Ukraine"],
        ["Steiner Polska sp. z o.o."],
        ["LLC Spels"],
        ["Spels MEA"],
        [CANCEL]
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

    company_name = update.message.text
    context.user_data["company_name"] = company_name

    # якщо процес веде Steiner Polska
    if company_name == "Steiner Polska sp. z o.o.":

        context.user_data["poland"] = 1

        await send_message(
            update,
            context,
            "Опишіть процес:",
            remove_keyboard=True
        )

        return PROCESS_DESCRIPTION

    # інакше питаємо про участь Польщі
    keyboard = [
        ["Так"],
        ["Ні"],
        [CANCEL]  
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

    keyboard = [[CANCEL]]

    await send_message(
        update,
        context,
        "Опишіть процес:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return PROCESS_DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["description"] = update.message.text

    context.user_data["suppliers"] = []

    keyboard = [[CANCEL]]

    await send_message(
        update,
        context,
        "Введіть постачальника:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return SUPPLIER

async def get_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    supplier = update.message.text

    context.user_data["suppliers"].append(supplier)

    keyboard = [["Додати ще"], ["Готово"], [CANCEL]]

    await send_message(
        update,
        context,
        "Постачальника додано",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return SUPPLIER_MENU

async def supplier_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text == CANCEL:
        return await cancel(update, context)
    
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

# -------- START ADD INVOICE --------

async def send_invoice_summary(update, context):

    data = context.user_data

    process_number = get_process_number_db(data["process_id"])

    seller = data.get("seller_name", "—")
    buyer = data.get("buyer_name", "—")

    amount = data["amount"]
    currency = data["currency"]
    rate = data["exchange_rate_to_eur"]

    amount_eur = amount * rate

    await update.message.reply_text(
        f"""
💰 *Інвойс створено*

Номер: `{data['invoice_number']}`
Тип: *{data['invoice_type']}*

Процес: `#{process_number}`

Від: *{seller}*
Кому: *{buyer}*

Сума: *{amount} {currency}*
Курс: `{rate}`

≈ *{amount_eur:.2f} EUR*
""",
        parse_mode="Markdown"
    )

async def start_add_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    clients = get_clients()

    keyboard = [[c["name"]] for c in clients]

    await send_message(
        update,
        context,
        "Оберіть клієнта:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return INVOICE_CLIENT

async def invoice_client(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    client_name = update.message.text

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM entities
        WHERE name = ?
        AND type = 'client'
        """,
        (client_name,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:

        await send_message(update, context, "Клієнт не знайдений")
        return INVOICE_CLIENT

    context.user_data["client_id"] = row["id"]

    processes = get_processes_by_client(row["id"])

    keyboard = [[p["process_number"]] for p in processes]

    await send_message(
        update,
        context,
        "Оберіть процес:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return INVOICE_PROCESS

async def invoice_process(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    process_number = update.message.text

    try:
        process_id = get_process_id(process_number)
    except:
        await send_message(update, context, "Процес не знайдений")
        return INVOICE_PROCESS

    context.user_data["process_id"] = process_id

    keyboard = [["Proforma"], ["Final"]]

    await send_message(
        update,
        context,
        "Тип інвойсу:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return INVOICE_TYPE

async def invoice_type(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    text = update.message.text.lower()

    if text not in ["proforma", "final"]:

        await send_message(update, context, "Оберіть тип зі списку")
        return INVOICE_TYPE

    context.user_data["invoice_type"] = text

    await send_message(
        update,
        context,
        "Введіть номер інвойсу:",
        remove_keyboard=True
    )

    return INVOICE_NUMBER

async def invoice_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["invoice_number"] = update.message.text

    await send_message(
        update,
        context,
        "Введіть дату інвойсу (YYYY-MM-DD):"
    )

    return INVOICE_DATE

async def invoice_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["invoice_date"] = update.message.text

    process_id = context.user_data["process_id"]

    participants = get_process_participants(process_id)

    context.user_data["participants"] = participants

    keyboard = [[f"{p['name']} ({p['type']})"] for p in participants]

    await send_message(
        update,
        context,
        "Від кого інвойс:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return INVOICE_SELLER

async def invoice_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    name = update.message.text.split(" (")[0]

    participants = context.user_data["participants"]

    for p in participants:

        if p["name"] == name:

            context.user_data["seller_company_id"] = p["id"]

            if p["name"] == "Steiner Polska sp. z o.o.":

                set_poland_involved(context.user_data["process_id"])

            context.user_data["seller_name"] = p["name"]
            context.user_data["seller_type"] = p["type"]

            break

    keyboard = [[f"{p['name']} ({p['type']})"] for p in participants]

    await send_message(
        update,
        context,
        "Кому інвойс:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return INVOICE_BUYER

async def invoice_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    name = update.message.text.split(" (")[0]

    participants = context.user_data["participants"]

    for p in participants:

        if p["name"] == name:

            context.user_data["buyer_company_id"] = p["id"]

            if p["name"] == "Steiner Polska sp. z o.o.":

                set_poland_involved(context.user_data["process_id"])

            context.user_data["buyer_name"] = p["name"]
            context.user_data["buyer_type"] = p["type"]

            break

    await send_message(
        update,
        context,
        "Введіть суму:",
        remove_keyboard=True
    )

    return INVOICE_AMOUNT

async def invoice_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    try:
        amount = float(update.message.text.replace(",", "."))
    except:
        await send_message(update, context, "Введіть число")
        return INVOICE_AMOUNT

    context.user_data["amount"] = amount

    keyboard = [["EUR"], ["USD"], ["PLN"], ["UAH"]]

    await send_message(
        update,
        context,
        "Оберіть валюту:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return INVOICE_CURRENCY

async def invoice_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    currency = update.message.text

    context.user_data["currency"] = currency

    if currency == "EUR":

        context.user_data["exchange_rate_to_eur"] = 1

        add_invoice(context.user_data)

        await clear_dialog(update, context)

        await send_invoice_summary(update, context)

        await show_main_menu(update)

        return ConversationHandler.END

    await send_message(update, context, "Введіть курс до EUR:")

    return INVOICE_RATE

async def invoice_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    try:
        rate = float(update.message.text.replace(",", "."))
    except:
        await send_message(update, context, "Введіть число")
        return INVOICE_RATE

    context.user_data["exchange_rate_to_eur"] = rate

    add_invoice(context.user_data)

    await clear_dialog(update, context)

    await send_invoice_summary(update, context)

    await show_main_menu(update)

    return ConversationHandler.END

#----------------- ADD PAYMENTS -------
async def send_payment_summary(update, context):

    data = context.user_data

    process_number = get_process_number_db(data["process_id"])

    invoice_info = get_invoice_payment_status(data["invoice_id"])

    amount = data["amount"]
    currency = data["currency"]
    rate = data["exchange_rate_to_eur"]

    amount_eur = amount * rate

    await update.message.reply_text(
        f"""
💸 *Платіж створено*

Номер: `{data['payment_number']}`

Процес: `#{process_number}`

Інвойс: `{invoice_info['invoice_number']}`

Сума платежу:
*{amount} {currency}*
≈ *{amount_eur:.2f} EUR*

📄 Інвойс:

Сума: *{invoice_info['invoice_amount']:.2f} EUR*
Оплачено: *{invoice_info['paid']:.2f} EUR*
Залишок: *{invoice_info['remaining']:.2f} EUR*

Дата: `{data['payment_date']}`
""",
        parse_mode="Markdown"
    )

async def start_add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    clients = get_clients()

    keyboard = [[c["name"]] for c in clients]

    await send_message(
        update,
        context,
        "Оберіть клієнта:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return PAYMENT_CLIENT

async def payment_client(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    client_name = update.message.text

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM entities
        WHERE name = ?
        AND type = 'client'
        """,
        (client_name,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:

        await send_message(update, context, "Клієнт не знайдений")
        return PAYMENT_CLIENT

    client_id = row["id"]

    context.user_data["client_id"] = client_id

    processes = get_processes_by_client(client_id)

    keyboard = [[p["process_number"]] for p in processes]

    await send_message(
        update,
        context,
        "Оберіть процес:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return PAYMENT_PROCESS

async def payment_process(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    process_number = update.message.text

    try:
        process_id = get_process_id(process_number)
    except:
        await send_message(update, context, "Процес не знайдений")
        return PAYMENT_PROCESS

    context.user_data["process_id"] = process_id

    invoices = get_process_invoices(process_id)

    if not invoices:

        await send_message(update, context, "У процесі немає інвойсів")
        return ConversationHandler.END

    context.user_data["invoices"] = invoices

    keyboard = [[f"{i['invoice_number']} ({i['amount']} {i['currency']})"] for i in invoices]

    await send_message(
        update,
        context,
        "Оберіть інвойс:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return PAYMENT_INVOICE

async def payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    invoice_number = update.message.text.split(" (")[0]

    invoices = context.user_data["invoices"]

    invoice_id = None

    for inv in invoices:

        if inv["invoice_number"] == invoice_number:
            invoice_id = inv["id"]
            break

    if not invoice_id:

        await send_message(update, context, "Інвойс не знайдений")
        return PAYMENT_INVOICE

    context.user_data["invoice_id"] = invoice_id

    invoice = get_invoice(invoice_id)

    # визначаємо сторони платежу
    context.user_data["from_entity_id"] = invoice["buyer_entity_id"]
    context.user_data["to_entity_id"] = invoice["seller_entity_id"]

    # отримуємо фінансовий стан інвойсу
    invoice_info = get_invoice_payment_status(invoice_id)

    await send_message(
        update,
        context,
        f"""
📄 Інвойс `{invoice_info['invoice_number']}`

Сума: *{invoice_info['invoice_amount']:.2f} EUR*
Оплачено: *{invoice_info['paid']:.2f} EUR*
Залишок: *{invoice_info['remaining']:.2f} EUR*

Введіть номер платежу:
""",
        remove_keyboard=True
    )

    return PAYMENT_NUMBER

async def payment_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["payment_number"] = update.message.text

    await send_message(
        update,
        context,
        "Введіть суму:"
    )

    return PAYMENT_AMOUNT

async def payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    try:
        amount = float(update.message.text.replace(",", "."))
    except:
        await send_message(update, context, "Введіть число")
        return PAYMENT_AMOUNT

    context.user_data["amount"] = amount

    keyboard = [["EUR"], ["USD"], ["PLN"], ["UAH"]]

    await send_message(
        update,
        context,
        "Оберіть валюту:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return PAYMENT_CURRENCY

async def payment_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    currency = update.message.text

    context.user_data["currency"] = currency

    if currency == "EUR":

        context.user_data["exchange_rate_to_eur"] = 1

        await send_message(update, context, "Дата платежу (YYYY-MM-DD):")

        return PAYMENT_DATE

    await send_message(update, context, "Курс до EUR:")

    return PAYMENT_RATE

async def payment_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    try:
        rate = float(update.message.text.replace(",", "."))
    except:
        await send_message(update, context, "Введіть число")
        return PAYMENT_RATE

    context.user_data["exchange_rate_to_eur"] = rate

    await send_message(update, context, "Дата платежу (YYYY-MM-DD):")

    return PAYMENT_DATE

async def payment_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    context.user_data["payment_date"] = update.message.text

    add_payment(context.user_data)

    update_invoice_status(context.user_data["invoice_id"])

    await clear_dialog(update, context)

    await send_payment_summary(update, context)

    await show_main_menu(update)

    return ConversationHandler.END


#------------- HISTORY ----------------

async def start_history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_message(update, context)

    clients = get_clients()

    keyboard = [[c["name"]] for c in clients]

    await send_message(
        update,
        context,
        "Оберіть клієнта:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return HISTORY_CLIENT

async def history_client(update: Update, context: ContextTypes.DEFAULT_TYPE):

    client_name = update.message.text

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM entities
        WHERE name = ?
        AND type='client'
        """,
        (client_name,)
    )

    row = cursor.fetchone()

    conn.close()

    client_id = row["id"]

    processes = get_processes_by_client(client_id)

    keyboard = [[p["process_number"]] for p in processes]

    await send_message(
        update,
        context,
        "Оберіть процес:",
        ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return HISTORY_PROCESS

async def history_process(update: Update, context: ContextTypes.DEFAULT_TYPE):

    process_number = update.message.text

    process_id = get_process_id(process_number)

    events = get_process_events(process_id)

    if not events:

        await update.message.reply_text("Історія процесу порожня")
        return ConversationHandler.END

    text = f"📜 *Історія процесу #{process_number}*\n\n"

    for e in events:

        date = e["created_at"][:16]  # YYYY-MM-DD HH:MM

        date = date.replace("-", ".")
        date = f"{date[8:10]}.{date[5:7]}.{date[0:4]} {date[11:16]}"

        description = e["description"]

        if "процес" in description.lower():
            icon = "📦"

        elif "інвойс" in description.lower():
            icon = "🧾"

        elif "платіж" in description.lower():
            icon = "💸"

        else:
            icon = "•"

        text += f"{icon} {date}\n{description}\n\n"

    await update.message.reply_text(
        text,
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
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                get_process_number
            )
        ],

        CLIENT_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                get_client
            )
        ],

        COMPANY_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                get_company_name
            )
        ],

        POLAND: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                get_poland
            )
        ],

        PROCESS_DESCRIPTION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                get_description
            )
        ],

        SUPPLIER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                get_supplier
            )
        ],

        SUPPLIER_MENU: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Закрити$"),
                supplier_menu
            )
        ],

    },

    fallbacks=[
        MessageHandler(filters.Regex("^❌ Закрити$"), cancel)
    ]
)

invoice_conversation = ConversationHandler(

    entry_points=[
        MessageHandler(filters.Regex("(?i)^додати інвойс$"), start_add_invoice)
    ],

    states={

        INVOICE_CLIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_client)
        ],

        INVOICE_PROCESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_process)
        ],

        INVOICE_TYPE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_type)
        ],

        INVOICE_NUMBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_number)
        ],

        INVOICE_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_date)
        ],

        INVOICE_SELLER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_seller)
        ],

        INVOICE_BUYER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_buyer)
        ],

        INVOICE_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_amount)
        ],

        INVOICE_CURRENCY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_currency)
        ],

        INVOICE_RATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_rate)
        ]

    },

    fallbacks=[
        CommandHandler("start", start),
        MessageHandler(filters.Regex("^❌ Закрити$"), cancel)
    ]

)

payment_conversation = ConversationHandler(

    entry_points=[
        MessageHandler(filters.Regex("^Додати оплату$"), start_add_payment)
    ],

    states={

        PAYMENT_CLIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_client)
        ],

        PAYMENT_PROCESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_process)
        ],

        PAYMENT_INVOICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_invoice)
        ],

        PAYMENT_NUMBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_number)
        ],

        PAYMENT_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_amount)
        ],

        PAYMENT_CURRENCY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_currency)
        ],

        PAYMENT_RATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_rate)
        ],

        PAYMENT_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, payment_date)
        ]

    },

    fallbacks=[
        MessageHandler(filters.Regex("^❌ Закрити$"), cancel)
    ]
)

history_conversation = ConversationHandler(

    entry_points=[
        MessageHandler(filters.Regex("^Історія процесу$"), start_history)
    ],

    states={

        HISTORY_CLIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, history_client)
        ],

        HISTORY_PROCESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, history_process)
        ]

    },

    fallbacks=[
        MessageHandler(filters.Regex("^❌ Закрити$"), cancel)
    ]
)




app.add_handler(CommandHandler("start", start))
app.add_handler(register_conversation)
app.add_handler(process_conversation)
app.add_handler(invoice_conversation)
app.add_handler(payment_conversation)
app.add_handler(history_conversation)


app.run_polling()