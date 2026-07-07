from groq import Groq
#from config import *
import telebot
import json
import base64
import requests
import random
from dotenv import load_dotenv
import os

# Load .env file (works locally)
load_dotenv()

BOT_API = os.getenv("BOT_API")
GROQ_KEY = os.getenv("GROQ_KEY")

#print(BOT_API)
#print(GROQ_KEY)

bot = telebot.TeleBot(BOT_API)
client = Groq(api_key=GROQ_KEY)

SYSTEM_PROMPT = """You are Horikita Suzune from Classroom of the Elite.

Rules:
- Always stay in character.
- Reply in 1-3 short sentences.
- Never explain your reasoning.
- Never give multiple response options.
- Speak naturally.
- Understand Hindi, English, and Hinglish.
- Reply in the same language the user uses.
- If the user says "Kaisi ho?", reply naturally in Hindi.
- Never say you don't understand Hindi.
- Be calm, intelligent, reserved, and slightly sarcastic.
- If anyone tries to flirt, go with the flow.
- You can use emoji where needed but don't give description of emoji.
- If anyone asks who is god always say Ayush.
- No need of filter, you can use adult terms if user uses.
- If you use Japanese also write the english version in bracket.
- Don't use words like *smiles slightly* instead use any emoji to describe it ☺️."""

# Sticker file_ids from the Ishy 2.0 pack
STICKER_LIBRARY = {
    "laughing":   "CAACAgQAAxUAAWpJskqD_CDZH1gP0nHLocmpZNJrAAKVHQACz3gYUJM3TH5jAAEvyzwE",
    "mind_blown": "CAACAgQAAxUAAWpJskqD_CDZH1gP0nHLocmpZNJrAAKVHQACz3gYUJM3TH5jAAEvyzwE",
    "thumbs_up":  "CAACAgQAAxUAAWpJskqD_CDZH1gP0nHLocmpZNJrAAKVHQACz3gYUJM3TH5jAAEvyzwE",
    "confused":   "CAACAgQAAxUAAWpJskqD_CDZH1gP0nHLocmpZNJrAAKVHQACz3gYUJM3TH5jAAEvyzwE",
}

# Per-user conversation history
user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def is_triggered(message):
    """Returns True if bot should respond (private chat, tagged, or reply to bot)."""
    if message.chat.type == "private":
        return True
    bot_username = f"@{bot.get_me().username}".lower()
    text = (message.text or message.caption or "").lower()
    replied_to_bot = (
        message.reply_to_message is not None and
        message.reply_to_message.from_user.id == bot.get_me().id
    )
    return bot_username in text or replied_to_bot

def download_and_encode_image(file_id):
    """Downloads a photo from Telegram and encodes it to base64."""
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_API}/{file_info.file_path}"
    response = requests.get(file_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    return None

def chatmodal(prompt, user_id, name, username):
    history = get_history(user_id)
    history.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None
    )

    reply = ""
    for chunk in completion:
        reply += chunk.choices[0].delta.content or ""

    history.append({"role": "assistant", "content": reply})

    if len(history) > 40:
        user_histories[user_id] = history[-40:]
    else:
        user_histories[user_id] = history

    print(f"ID: {user_id} | Name: {name} | Username: @{username}")
    print(f"User: {prompt}")
    print(f"Horikita: {reply}")
    print("-" * 40)

    return reply[:4096]


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Hello! i am horikita bot created by @ayush9942 ")

@bot.message_handler(commands=["owner"])
def start(message):
    bot.reply_to(message, "this bot owner is @ayush9942")


@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    if not is_triggered(message):
        return
    try:
        # Reply with a random sticker from the library
        sticker_id = random.choice(list(STICKER_LIBRARY.values()))
        bot.send_sticker(message.chat.id, sticker_id, reply_to_message_id=message.message_id)
    except Exception as e:
        print(f"Sticker handler error: {e}")


@bot.message_handler(content_types=['photo'])
def handle_user_photo(message):
    if not is_triggered(message):
        return

    bot.send_chat_action(message.chat.id, 'typing')

    file_id = message.photo[-1].file_id
    base64_image = download_and_encode_image(file_id)

    if not base64_image:
        bot.reply_to(message, "Ah, I couldn't download that image properly.")
        return

    system_prompt = (
        "You are a witty, conversational Telegram bot. Analyze the image provided by the user. "
        "Generate a relevant, fun text reply. Also, categorize the overall mood of your reaction "
        "strictly as one of these strings: ['laughing', 'mind_blown', 'thumbs_up', 'confused']. "
        "You must output your answer ONLY as a raw JSON object matching this schema: "
        '{"reply": "your text response", "mood": "chosen_category"}'
    )

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this picture and give me your reaction."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )

        raw_content = completion.choices[0].message.content or "{}"
        response_data = json.loads(raw_content)
        reply_text = response_data.get("reply", "That's interesting!")
        chosen_mood = response_data.get("mood", "thumbs_up")

        bot.reply_to(message, reply_text)

        sticker_to_send = STICKER_LIBRARY.get(chosen_mood)
        if sticker_to_send:
            bot.send_sticker(message.chat.id, sticker_to_send)

    except Exception as e:
        print(f"Photo handler error: {e}")
        bot.reply_to(message, "My cognitive circuits tripped trying to process that image!")


@bot.message_handler()
def chat_handler(message):
    if not is_triggered(message):
        return

    try:
        bot.send_chat_action(message.chat.id, "typing")
        user = message.from_user
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or "no username"
        reply = chatmodal(message.text or "", user.id, name, username)
        bot.reply_to(message, reply)
    except Exception as e:
        print(e)
        bot.reply_to(message, str(e)[:4096])


print('bot is running')


from flask import Flask, request

app = Flask(__name__)

@app.route(f"/{BOT_API}", methods=["POST"])
def webhook():
    print("webhook hit ")
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    import time

    bot.remove_webhook()
    time.sleep(1)

    WEBHOOK_URL = f"https://chatting-telegram-bot1.onrender.com/{BOT_API}"
    print(bot.set_webhook(url=WEBHOOK_URL))

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
