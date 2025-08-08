
import telebot
import os
import subprocess
import threading
import time
import logging
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1> hosting Bot Live ✅</h1>"

if __name__ == '__main__':
    app.run(debug=True)

# --- Bot Configuration ---
BOT_TOKEN = "8345947714:AAENEX0AOb0_fOD9kd3GJjpDSECNytmVe8c"  # Replace with your actual bot token
UPLOAD_FOLDER = "uploads"  # Directory to store uploaded files
LOG_FILE = "bot.log"  # Log file name

# --- Configure Logging ---
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Initialize Bot ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- Create Uploads Folder if it doesn't exist ---
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Global Variables ---
running_processes = {}  # Dictionary to store running processes (filename: process)


# --- Helper Functions ---

def format_file_size(size_bytes):
    """Formats file size in a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_file_list():
    """Returns a list of files in the uploads folder with their sizes."""
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            files.append((filename, os.path.getsize(filepath)))
    return files


def run_python_script(filename, chat_id):
    """Runs a Python script in a separate thread and sends output to the bot."""
    global running_processes
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        process = subprocess.Popen(['python', filepath],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True)  # Capture output as text

        running_processes[filename] = process

        while True:
            output = process.stdout.readline()
            error = process.stderr.readline()

            if output:
                bot.send_message(chat_id, f"📜 Output from {filename}:\n`{output.strip()}`", parse_mode="Markdown")
                logging.info(f"Script {filename} output: {output.strip()}")
            if error:
                bot.send_message(chat_id, f"🚨 Error from {filename}:\n`{error.strip()}`", parse_mode="Markdown")
                logging.error(f"Script {filename} error: {error.strip()}")

            return_code = process.poll()
            if return_code is not None:
                del running_processes[filename]
                if return_code == 0:
                    bot.send_message(chat_id, f"✅ Script `{filename}` finished successfully.", parse_mode="Markdown")
                    logging.info(f"Script {filename} finished successfully.")
                else:
                    bot.send_message(chat_id, f"❌ Script `{filename}` finished with an error (return code: {return_code}).", parse_mode="Markdown")
                    logging.error(f"Script {filename} finished with error (return code: {return_code}).")
                break

            time.sleep(0.1)  # Avoid busy-waiting

    except FileNotFoundError:
        bot.send_message(chat_id, f"❌ File `{filename}` not found.", parse_mode="Markdown")
        logging.error(f"File {filename} not found.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ An error occurred while running `{filename}`: `{str(e)}`", parse_mode="Markdown")
        logging.exception(f"Error running script {filename}: {e}")


def install_package(package_name, chat_id):
    """Installs a Python package using pip."""
    try:
        bot.send_message(chat_id, f"⏳ Installing package `{package_name}`...", parse_mode="Markdown")
        process = subprocess.run(['pip', 'install', package_name, '-U'],
                                   capture_output=True, text=True)  # Capture output

        if process.returncode == 0:
            bot.send_message(chat_id, f"✅ Package `{package_name}` installed successfully.", parse_mode="Markdown")
            logging.info(f"Package {package_name} installed successfully.")
        else:
            bot.send_message(chat_id, f"❌ Error installing package `{package_name}`:\n`{process.stderr}`", parse_mode="Markdown")
            logging.error(f"Error installing package {package_name}: {process.stderr}")

    except Exception as e:
        bot.send_message(chat_id, f"❌ An error occurred while installing `{package_name}`: `{str(e)}`", parse_mode="Markdown")
        logging.exception(f"Error installing package {package_name}: {e}")


# --- Command Handlers ---

@bot.message_handler(commands=['start'])
def start(message):
    """Handles the /start command."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("📁 List Files")
    item2 = telebot.types.KeyboardButton("⚙️ Manage Files")
    item3 = telebot.types.KeyboardButton("🚀 Run Script")
    item4 = telebot.types.KeyboardButton("📦 Install Package")
    item5 = telebot.types.KeyboardButton("ℹ️ Help")
    markup.add(item1, item2, item3, item4, item5)

    bot.send_message(message.chat.id,
                     "👋 Hello! I'm your Python Hosting Bot.  I can run your Python scripts.\n\n"
                     "Use the buttons below or the following commands:\n"
                     "/list - List uploaded files\n"
                     "/run [filename] - Run a Python script\n"
                     "/install [package] - Install a Python package\n"
                     "/help - Show available commands\n"
                     "/manage -  Manage your uploaded files\n"
                     "Just send me a Python file to upload it! 📤",
                     reply_markup=markup)
    logging.info(f"User {message.from_user.id} started the bot.")


@bot.message_handler(commands=['help'])
def help(message):
    """Handles the /help command."""
    help_text = """
Here are the available commands:

/start - Start the bot and show the main menu.
/list - List all uploaded Python files.
/run [filename] - Run a Python script (e.g., `/run my_script.py`).
/install [package] - Install a Python package using pip (e.g., `/install requests`).
/help - Show this help message.
/manage - Manage your uploaded files(Delete ,Show Size).

You can also upload Python files directly by sending them to the bot. 📤
"""
    bot.send_message(message.chat.id, help_text)
    logging.info(f"User {message.from_user.id} requested help.")

@bot.message_handler(commands=['manage'])
def manage_files(message):
    """Handles the /manage command."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("🗑️ Delete File")
    item2 = telebot.types.KeyboardButton("📊 Show File Size")
    item3 = telebot.types.KeyboardButton("Back to Main Menu")  # Back button
    markup.add(item1, item2, item3)

    bot.send_message(message.chat.id, "📁 File Management Options:", reply_markup=markup)
    logging.info(f"User {message.from_user.id} entered file management.")

@bot.message_handler(func=lambda message: message.text == "🗑️ Delete File")
def delete_file_selection(message):
    """Handles the "Delete File" option."""
    files = get_file_list()
    if not files:
        bot.send_message(message.chat.id, "No files to delete.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for filename, _ in files:
        markup.add(telebot.types.KeyboardButton(f"Delete: {filename}"))
    markup.add(telebot.types.KeyboardButton("Cancel"))
    bot.send_message(message.chat.id, "Choose a file to delete:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.startswith("Delete: "))
def delete_file(message):
    """Deletes the selected file."""
    filename = message.text[len("Delete: "):]
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            bot.send_message(message.chat.id, f"✅ File `{filename}` deleted successfully.", parse_mode="Markdown", reply_markup=get_main_menu_markup())
            logging.info(f"File {filename} deleted by user {message.from_user.id}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error deleting file `{filename}`: `{str(e)}`", parse_mode="Markdown", reply_markup=get_main_menu_markup())
            logging.error(f"Error deleting file {filename} by user {message.from_user.id}: {e}")
    else:
        bot.send_message(message.chat.id, f"❌ File `{filename}` not found.", parse_mode="Markdown", reply_markup=get_main_menu_markup())


@bot.message_handler(func=lambda message: message.text == "📊 Show File Size")
def show_file_size_selection(message):
    """Handles the "Show File Size" option."""
    files = get_file_list()
    if not files:
        bot.send_message(message.chat.id, "No files uploaded yet.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for filename, _ in files:
        markup.add(telebot.types.KeyboardButton(f"Size: {filename}"))
    markup.add(telebot.types.KeyboardButton("Cancel"))  # Added Cancel button
    bot.send_message(message.chat.id, "Choose a file to show its size:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.startswith("Size: "))
def show_file_size(message):
    """Shows the size of the selected file."""
    filename = message.text[len("Size: "):]
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        formatted_size = format_file_size(file_size)
        bot.send_message(message.chat.id, f"📏 File `{filename}` size: `{formatted_size}`", parse_mode="Markdown", reply_markup=get_main_menu_markup())
        logging.info(f"File size of {filename} shown to user {message.from_user.id}.")
    else:
        bot.send_message(message.chat.id, f"❌ File `{filename}` not found.", parse_mode="Markdown", reply_markup=get_main_menu_markup())

@bot.message_handler(commands=['list'])
def list_files(message):
    """Handles the /list command."""
    files = get_file_list()

    if not files:
        bot.send_message(message.chat.id, "No files uploaded yet.")
        return

    file_list_text = "Uploaded files:\n"
    for filename, file_size in files:
        formatted_size = format_file_size(file_size)
        file_list_text += f"- `{filename}` ({formatted_size})\n"

    bot.send_message(message.chat.id, file_list_text, parse_mode="Markdown")
    logging.info(f"User {message.from_user.id} listed files.")


@bot.message_handler(commands=['run'])
def run_script_command(message):
    """Handles the /run command."""
    try:
        filename = message.text.split(' ', 1)[1].strip()
        if not filename.endswith(".py"):
            bot.send_message(message.chat.id, "❌ Please provide a Python file name ending with `.py`.")
            return
        run_script(message, filename)  # Call the common run_script function

    except IndexError:
        bot.send_message(message.chat.id, "❌ Please provide a filename to run (e.g., `/run my_script.py`).")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An unexpected error occurred: `{str(e)}`", parse_mode="Markdown")
        logging.exception(f"Error in /run command by user {message.from_user.id}: {e}")


@bot.message_handler(commands=['install'])
def install_package_command(message):
    """Handles the /install command."""
    try:
        package_name = message.text.split(' ', 1)[1].strip()
        install_package(package_name, message.chat.id)
    except IndexError:
        bot.send_message(message.chat.id, "❌ Please provide a package name to install (e.g., `/install requests`).")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An unexpected error occurred: `{str(e)}`", parse_mode="Markdown")
        logging.exception(f"Error in /install command by user {message.from_user.id}: {e}")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Handles document uploads (specifically Python files)."""
    try:
        if message.document.file_name.endswith('.py'):
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            filename = message.document.file_name
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            with open(filepath, 'wb') as new_file:
                new_file.write(downloaded_file)

            bot.send_message(message.chat.id, f"✅ File `{filename}` saved successfully!", parse_mode="Markdown")
            logging.info(f"File {filename} uploaded by user {message.from_user.id}.")
        else:
            bot.send_message(message.chat.id, "❌ Only Python files (.py) are allowed.")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred during file upload: `{str(e)}`", parse_mode="Markdown")
        logging.exception(f"Error handling document upload by user {message.from_user.id}: {e}")


# --- Button Handlers (Refactored) ---

def get_main_menu_markup():
    """Helper function to create the main menu keyboard markup."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("📁 List Files")
    item2 = telebot.types.KeyboardButton("⚙️ Manage Files")
    item3 = telebot.types.KeyboardButton("🚀 Run Script")
    item4 = telebot.types.KeyboardButton("📦 Install Package")
    item5 = telebot.types.KeyboardButton("ℹ️ Help")
    markup.add(item1, item2, item3, item4, item5)
    return markup

@bot.message_handler(func=lambda message: message.text == "Back to Main Menu" or message.text == "Cancel")
def back_to_main_menu(message):
    """Handles the "Back to Main Menu" button."""
    bot.send_message(message.chat.id, "Returning to main menu.", reply_markup=get_main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "📁 List Files")
def list_files_button(message):
    """Handles the "List Files" button."""
    list_files(message)  # Call the existing list_files function

@bot.message_handler(func=lambda message: message.text == "⚙️ Manage Files")
def manage_files_button(message):
    """Handles the "Manage Files" button."""
    manage_files(message)  # Call the existing manage_files function

def run_script(message, filename):
    """Runs a script (either from button or command)."""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        bot.send_message(message.chat.id, f"❌ File `{filename}` not found.", parse_mode="Markdown")
        return

    if filename in running_processes:
        bot.send_message(message.chat.id, f"❌ Script `{filename}` is already running. Please wait for it to finish or stop it manually.")
        return

    bot.send_message(message.chat.id, f"⏳ Running script `{filename}`...", parse_mode="Markdown")
    threading.Thread(target=run_python_script, args=(filename, message.chat.id)).start()
    logging.info(f"Script {filename} started by user {message.from_user.id}.")

@bot.message_handler(func=lambda message: message.text == "🚀 Run Script")
def run_script_button(message):
    """Handles the "Run Script" button."""
    files = get_file_list()
    if not files:
        bot.send_message(message.chat.id, "No files to run. Upload a Python file first!")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for filename, _ in files:
        markup.add(telebot.types.KeyboardButton(filename))  # Use filenames as button text
    markup.add(telebot.types.KeyboardButton("Cancel"))  # Added Cancel button
    bot.send_message(message.chat.id, "Choose a script to run:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.endswith(".py"))
def handle_script_selection(message):
    """Handles the selection of a script from the Run Script menu."""
    filename = message.text
    run_script(message, filename)  # Call the common run_script function

@bot.message_handler(func=lambda message: message.text == "📦 Install Package")
def install_package_button(message):
    """Handles the "Install Package" button."""
    bot.send_message(message.chat.id, "Please enter the package name to install (e.g., `requests`):", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_package_name)

def process_package_name(message):
    """Gets the package name from the user and installs it."""
    package_name = message.text.strip()
    if package_name:
        install_package(package_name, message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Package name cannot be empty.", reply_markup=get_main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "ℹ️ Help")
def help_button(message):
    """Handles the "Help" button."""
    help(message)  # Call the existing help function


# --- Main Loop ---
if __name__ == '__main__':
    try:
        logging.info("Bot started.")
        bot.infinity_polling()  # Use infinity_polling for better reconnection handling
    except Exception as e:
        logging.exception(f"Bot stopped due to an error: {e}")
    finally:
        logging.info("Bot stopped.")
