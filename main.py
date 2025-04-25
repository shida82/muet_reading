from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import openai
import requests
from bs4 import BeautifulSoup
from readability import Document
import json
import re

TELEGRAM_BOT_TOKEN = "xxx"
OPENAI_API_KEY = "xxx"

openai.api_key = OPENAI_API_KEY

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hai! Saya *MUET Reading Buddy* awak! 📚\n"
        "Saya akan bantu awak jadi lagi *power* dalam Reading MUET 💪\n\n"
        "✨ Paste je link artikel, kita terus mula belajar sama-sama!"
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Panduan MUET Buddy*\n\n"
        "/start - Mula semula\n"
        "/help - Bantuan\n"
        "/wordwhiz [perkataan] - Maksud & ayat contoh\n\n"
        "📖 Paste je link artikel untuk mulakan aktiviti!"
    )

# Menu aktiviti
async def show_activity_menu(update_or_query):
    keyboard = [
        [
            InlineKeyboardButton("📘 WordWhiz", callback_data='wordwhiz'),
            InlineKeyboardButton("📦 VocabVault", callback_data='vocabvault')
        ],
        [
            InlineKeyboardButton("🧠 Kuiz", callback_data='mcq'),
            InlineKeyboardButton("🎯 Soalan HOTS", callback_data='hots')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text("📌 Pilih aktiviti seterusnya kat bawah ni:", reply_markup=reply_markup)
    else:
        await update_or_query.edit_message_reply_markup(reply_markup=reply_markup)

# WordWhiz
async def wordwhiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Taip perkataan lepas arahan. Contoh: `/wordwhiz economy`", parse_mode="Markdown")
        return

    word = " ".join(context.args).strip()

    prompt = f"""
    Terangkan maksud perkataan berikut dalam Bahasa Melayu yang santai untuk pelajar MUET.
    Perkataan: {word}

    Sertakan:
    - Maksud mudah
    - Ayat BM
    - Ayat English
    - Terjemahan maksud ayat English
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Anda tutor MUET mesra & fasih BM."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=350
        )

        result = response.choices[0].message.content
        await update.message.reply_text(f"📘 *WordWhiz untuk:* `{word}`\n\n{result}", parse_mode="Markdown")
        await show_activity_menu(update)

    except Exception as e:
        print("🚨 WordWhiz error:", e)
        await update.message.reply_text("❌ Maaf, tak dapat proses. Cuba lagi ya!")

# VocabVault
async def vocabvault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        article_text = context.chat_data.get("article_text")
        if not article_text:
            await update.callback_query.edit_message_text("⚠️ Paste artikel dulu sebelum guna VocabVault.")
            return

        prompt = f"""
        Dari artikel ini, beri 10 perkataan penting untuk pelajar MUET.
        Untuk setiap perkataan:
        - Maksud (BM santai)
        - Ayat English
        - Terjemahan maksud ayat tu dalam BM

        Artikel: {article_text}
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tutor MUET bantu pelajar faham vocab dalam gaya santai."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=700
        )

        result = response.choices[0].message.content
        await update.callback_query.edit_message_text("📦 *VocabVault: 10 Perkataan Penting*\n\n" + result, parse_mode="Markdown")
        await show_activity_menu(update.callback_query)

    except Exception as e:
        print("🚨 VocabVault error:", e)
        await update.callback_query.edit_message_text("❌ Maaf, tak dapat jana VocabVault.")

# Handle artikel
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    if not user_input.startswith("http"):
        await update.message.reply_text("⚠️ Sila hantar link artikel penuh.")
        return

    await update.message.reply_text("⏳ Tengah proses artikel...")

    try:
        response = requests.get(user_input, timeout=10)
        doc = Document(response.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "html.parser")
        article_text = soup.get_text().strip()

        if len(article_text) < 100 or "javascript" in article_text.lower():
            await update.message.reply_text("⚠️ Artikel ni tak sesuai. Cuba link lain ya.")
            return

        trimmed_text = article_text[:2000]
        context.chat_data["article_text"] = trimmed_text

        summary_prompt = f"Ringkaskan artikel ini kepada 5 isi penting sahaja. Guna Bahasa Inggeris yang simple.\n\n{trimmed_text}"

        gpt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful MUET Reading tutor."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )

        summary = gpt_response.choices[0].message.content
        await update.message.reply_text("✅ Artikel berjaya diterima!\n\n📰 *Petikan Artikel:*\n" + trimmed_text[:800] + "...", parse_mode="Markdown")
        await update.message.reply_text("📌 *5 Isi Penting Artikel:*\n" + summary, parse_mode="Markdown")
        await show_activity_menu(update)

    except Exception as e:
        print("🚨 Error semasa proses artikel:", e)
        await update.message.reply_text("❌ Maaf, tak dapat proses artikel tu.")

# Butang menu
async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "wordwhiz":
        await query.edit_message_text("📘 *WordWhiz:* Taip perkataan yang awak tak faham guna `/wordwhiz [perkataan]`", parse_mode="Markdown")
    elif query.data == "vocabvault":
        await vocabvault(update, context)
    elif query.data == "mcq":
        await query.edit_message_text("🧠 *Kuiz Vocabulary:* (Interaktif akan datang!)")
    elif query.data == "hots":
        await query.edit_message_text("🎯 *Soalan HOTS:* (Akan datang!)")

# Mula bot
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("wordwhiz", wordwhiz))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app.add_handler(CallbackQueryHandler(handle_button_click, pattern='^(wordwhiz|vocabvault|mcq|hots)$'))

print("🚀 Bot sedang berjalan...")
app.run_polling()
