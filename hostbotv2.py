
import telebot
import os
import subprocess
import time
import shutil
from telebot import types
from flask import Flask

@app.route("/")
def index():
    return "Bot Web Server is running"

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# Run Flask in a daemon thread so it won't block program exit
thread = threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True),
    daemon=True
)
thread.start()
return thread


# Bot token (replace with your bot token)
BOT_TOKEN = "8345947714:AAGpUuJkkqn3l7FJLxYqtjjrTZ03_ubUe8I"  # Replace with your actual bot token

bot = telebot.TeleBot(BOT_TOKEN)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

active_processes = {}  # Keep track of running processes


def create_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton('⬆️ Upload File'),
        types.KeyboardButton('📁 List Files'),
        types.KeyboardButton('▶️ Run File'),
        types.KeyboardButton('🗑️ Delete File'),
        types.KeyboardButton('🚫 Stop File'),
        types.KeyboardButton('⚙️ Install Package')
    )
    keyboard.add(
        types.KeyboardButton('❌ Delete All Files'),
        types.KeyboardButton('🏓 Ping Check'),
    )
    return keyboard


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Use the buttons to manage your files and operations.",
                 reply_markup=create_keyboard())


@bot.message_handler(func=lambda message: message.text == "⬆️ Upload File")
def handle_upload_request(message):
    bot.reply_to(message, "Please send me the file you wish to upload.")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = os.path.join(UPLOAD_DIR, message.document.file_name)

        with open(file_name, 'wb') as f:
            f.write(downloaded_file)

        bot.reply_to(message, f"File '{message.document.file_name}' uploaded successfully. 🎉")
    except Exception as e:
        bot.reply_to(message, f"Error handling file upload: {e} 😥")


@bot.message_handler(func=lambda message: message.text == "📁 List Files")
def list_files(message):
    files = os.listdir(UPLOAD_DIR)
    if files:
        file_list = "\n".join([f"- {f}" for f in files])
        bot.reply_to(message, f"Uploaded files:\n{file_list} 📁")
    else:
        bot.reply_to(message, "No files uploaded yet 😥")


def show_file_run_option(message):
    files = os.listdir(UPLOAD_DIR)
    if not files:
        bot.reply_to(message, "No file to run 😥", reply_markup=create_keyboard())
        return

    keyboard = types.InlineKeyboardMarkup()
    for file_name in files:
        button = types.InlineKeyboardButton(text=file_name, callback_data=f"run_{file_name}")
        keyboard.add(button)
    bot.reply_to(message, "Choose file to run:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "▶️ Run File")
def handle_run_file_request(message):
    show_file_run_option(message)


def show_file_delete_option(message):
    files = os.listdir(UPLOAD_DIR)
    if not files:
        bot.reply_to(message, "No file to delete 😥", reply_markup=create_keyboard())
        return

    keyboard = types.InlineKeyboardMarkup()
    for file_name in files:
        button = types.InlineKeyboardButton(text=file_name, callback_data=f"del_{file_name}")
        keyboard.add(button)
    bot.reply_to(message, "Choose file to delete:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "🗑️ Delete File")
def handle_delete_request(message):
    show_file_delete_option(message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('run_'))
def run_file_callback(call):
    file_name = call.data[4:]
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if file_name in active_processes:
        bot.answer_callback_query(call.id, "File is already running!")
        return

    try:
        bot.answer_callback_query(call.id, "Running file...")
        # Run python file
        process = subprocess.Popen(['python', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active_processes[file_name] = process
        # run result
        stdout, stderr = process.communicate()
        output = stdout.decode('utf-8')
        error = stderr.decode('utf-8')
        response = f"Output:\n{output}\n"
        if error:
            response += f"Error:\n{error}"
        bot.send_message(call.message.chat.id, response)
        del active_processes[file_name]  # Remove after response
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error executing file: {e} 😥")


@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def delete_file_callback(call):
    file_name = call.data[4:]
    file_path = os.path.join(UPLOAD_DIR, file_name)
    try:
        os.remove(file_path)
        bot.answer_callback_query(call.id, "File deleted! 🗑️")
    except Exception as e:
        bot.answer_callback_query(call.id, "Error delete file!")
        bot.send_message(call.message.chat.id, f"Error deleting file: {e} 😥")


@bot.message_handler(func=lambda message: message.text == "🚫 Stop File")
def stop_file(message):
    keyboard = types.InlineKeyboardMarkup()
    if not active_processes:
        bot.reply_to(message, "No file to stop 😥", reply_markup=create_keyboard())
        return
    for file_name in active_processes:
        button = types.InlineKeyboardButton(text=file_name, callback_data=f"stop_{file_name}")
        keyboard.add(button)
    bot.reply_to(message, "Choose file to stop:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def stop_file_callback(call):
    file_name = call.data[5:]
    if file_name in active_processes:
        try:
            process = active_processes[file_name]
            process.terminate()
            del active_processes[file_name]
            bot.answer_callback_query(call.id, "File stopped! 🚫")
        except Exception as e:
            bot.answer_callback_query(call.id, "Error stop file!")
            bot.send_message(call.message.chat.id, f"Error stop file: {e} 😥")


@bot.message_handler(func=lambda message: message.text == "❌ Delete All Files")
def delete_all_files(message):
    try:
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR)
        bot.reply_to(message, "All files deleted! 🎉")
    except Exception as e:
        bot.reply_to(message, f"Error deleting all files: {e} 😥")


@bot.message_handler(func=lambda message: message.text == "🏓 Ping Check")
def ping_check(message):
    try:
        process = subprocess.Popen(['speedtest-cli', '--simple'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        output = stdout.decode('utf-8')
        bot.reply_to(message, f"Internet Speed:\n{output} 🏓")
    except FileNotFoundError:
        bot.reply_to(message, "Speedtest-cli is not installed. Please install it first.")
    except Exception as e:
        bot.reply_to(message, f"Error checking ping: {e} 😥")


@bot.message_handler(func=lambda message: message.text == "⚙️ Install Package")
def handle_install_package(message):
    bot.reply_to(message, "Please send the name of the package you want to install (e.g., 'requests').")
    bot.register_next_step_handler(message, install_package)


def install_package(message):
    package_name = message.text.strip()
    bot.reply_to(message, f"Installing package '{package_name}'. Please wait...")
    try:
        process = subprocess.Popen(['pip', 'install', package_name], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        output = stdout.decode('utf-8')
        error = stderr.decode('utf-8')

        response = f"Installation Output:\n{output}\n"
        if error:
            response += f"Error:\n{error}"

        bot.send_message(message.chat.id, response)
        bot.send_message(message.chat.id, f"Package '{package_name}' installed (or attempted to install).")

    except Exception as e:
        bot.reply_to(message, f"Error installing package: {e} 😥")


if __name__ == '__main__':
    print("Bot started...")
    bot.polling(none_stop=True)
