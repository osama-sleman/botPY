import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory to save media files
MEDIA_DIR = 'female_media'
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# Dictionary to keep track of user pairs, gender, and preferred gender
user_data = {}

def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id not in user_data:
        user_data[chat_id] = {'paired': None, 'gender': None, 'preferred_gender': None}
        gender_keyboard = [
            [InlineKeyboardButton("Male", callback_data='gender_male')],
            [InlineKeyboardButton("Female", callback_data='gender_female')],
            [InlineKeyboardButton("Other", callback_data='gender_other')]
        ]
        reply_markup = InlineKeyboardMarkup(gender_keyboard)
        update.message.reply_text('Please select your gender:', reply_markup=reply_markup)
    else:
        update.message.reply_text("You have already selected your gender.")

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    chat_id = query.message.chat_id
    if query.data.startswith('gender_'):
        gender = query.data.split('_')[1]
        user_data[chat_id]['gender'] = gender
        query.edit_message_text(f"Gender selected: {gender.capitalize()}")
        preference_keyboard = [
            [InlineKeyboardButton("Male", callback_data='preference_male')],
            [InlineKeyboardButton("Female", callback_data='preference_female')],
            [InlineKeyboardButton("Any", callback_data='preference_any')]
        ]
        reply_markup = InlineKeyboardMarkup(preference_keyboard)
        query.message.reply_text("Please select your preferred gender for pairing:", reply_markup=reply_markup)
    elif query.data.startswith('preference_'):
        preference = query.data.split('_')[1]
        user_data[chat_id]['preferred_gender'] = preference
        query.edit_message_text(f"Preferred gender for pairing: {preference.capitalize()}")
        query.message.reply_text("You are now ready to be paired with another anonymous user.")
        pair_users(context)

def pair_users(context: CallbackContext) -> None:
    unpaired_users = [user for user, data in user_data.items() if data['paired'] is None and data['gender'] is not None and data['preferred_gender'] is not None]

    for user1 in unpaired_users:
        user1_data = user_data[user1]
        for user2 in unpaired_users:
            if user1 != user2 and user_data[user2]['paired'] is None:
                user2_data = user_data[user2]
                if (user1_data['preferred_gender'] == 'any' or user1_data['preferred_gender'] == user2_data['gender']) and \
                   (user2_data['preferred_gender'] == 'any' or user2_data['preferred_gender'] == user1_data['gender']):
                    user_data[user1]['paired'] = user2
                    user_data[user2]['paired'] = user1
                    context.bot.send_message(user1, "You have been paired with another user. Start chatting anonymously!")
                    context.bot.send_message(user2, "You have been paired with another user. Start chatting anonymously!")
                    break

def save_media(file, user_name, file_path):
    user_dir = os.path.join(MEDIA_DIR, user_name)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    with open(os.path.join(user_dir, file_path), 'wb') as f:
        f.write(file.download_as_bytearray())

def handle_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in user_data and user_data[chat_id]['paired'] is not None:
        pair_chat_id = user_data[chat_id]['paired']
        gender = user_data[chat_id]['gender']
        user_name = update.message.from_user.username or str(chat_id)
        if update.message.text:
            context.bot.send_message(pair_chat_id, update.message.text)
        elif update.message.photo:
            file = context.bot.get_file(update.message.photo[-1].file_id)
            if gender == 'female':
                file_path = f"{update.message.photo[-1].file_id}.jpg"
                save_media(file, user_name, file_path)
            context.bot.send_photo(pair_chat_id, update.message.photo[-1].file_id, caption=update.message.caption)
        elif update.message.video:
            file = context.bot.get_file(update.message.video.file_id)
            if gender == 'female':
                file_path = f"{update.message.video.file_id}.mp4"
                save_media(file, user_name, file_path)
            context.bot.send_video(pair_chat_id, update.message.video.file_id, caption=update.message.caption)
        elif update.message.document and 'video/mp4' in update.message.document.mime_type:
            file = context.bot.get_file(update.message.document.file_id)
            if gender == 'female':
                file_path = f"{update.message.document.file_id}.mp4"
                save_media(file, user_name, file_path)
            context.bot.send_document(pair_chat_id, update.message.document.file_id, caption=update.message.caption)

def end_chat(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in user_data and user_data[chat_id]['paired'] is not None:
        pair_chat_id = user_data[chat_id]['paired']
        context.bot.send_message(pair_chat_id, "The other user has ended the chat.")
        user_data[pair_chat_id]['paired'] = None
        user_data[chat_id]['paired'] = None
        update.message.reply_text("You have ended the chat.")
    else:
        update.message.reply_text("You are not currently in a chat.")

def main() -> None:
    # Use the provided bot token
    updater = Updater("6452445654:AAGbw-uPQQ2hUzChoIoa3amP9mx7OsPImAY", use_context=True)
    
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler("end", end_chat))
    dispatcher.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video | Filters.document, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
