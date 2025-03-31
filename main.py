import telebot
import requests
import json
import random
import string

# Telegram bot tokenini shu yerga qo'ying
TOKEN = "7290637755:AAGvGnOKGQBANL3HWvZqK7_4Fp7vhWZAMDs"
bot = telebot.TeleBot(TOKEN)

# Request ID yaratish funksiyasi
def generate_request_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=16))

# Telefon raqamni qabul qilish uchun handler
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Salom! Telefon raqamingizni 99888XXXX formatida kiriting:")
    bot.register_next_step_handler(message, get_phone_number)

def get_phone_number(message):
    if not (message.text.isdigit() and len(message.text) >= 9):
        bot.send_message(message.chat.id, "Noto‘g‘ri format! Iltimos, 99888XXXX shaklida kiriting:")
        bot.register_next_step_handler(message, get_phone_number)
    else:
        phone_number = message.text
        bot.send_message(message.chat.id, "Necha marta yuborilsin? (1 dan 6 gacha):")
        bot.register_next_step_handler(message, send_sms_request, phone_number)

def send_sms_request(message, phone_number):
    if not (message.text.isdigit() and 1 <= int(message.text) <= 6):
        bot.send_message(message.chat.id, "Iltimos, 1 dan 6 gacha son kiriting:")
        bot.register_next_step_handler(message, send_sms_request, phone_number)
        return
    
    attempts = int(message.text)
    url = "https://kontrakt-api.edu.uz/Account/SendSMSCode"
    headers = {
        "Sec-Ch-Ua-Platform": "\"Linux\"",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "Sec-Ch-Ua": "\"Chromium\";v=\"133\", \"Not(A:Brand\";v=\"99\"",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Origin": "https://kontrakt.edu.uz",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://kontrakt.edu.uz/",
        "Accept-Encoding": "gzip, deflate, br"
    }

    for _ in range(attempts):
        request_id = generate_request_id()
        cookies = {"requestId": request_id}
        data = {
            "phonenumber": f"+{phone_number[:3]}-{phone_number[3:5]}-{phone_number[5:]}",
            "password": "52898000120044",
            "passwordconfirm": "52898000120044",
            "smscode": ""
        }

        response = requests.post(url, headers=headers, cookies=cookies, data=json.dumps(data))
        
        if response.status_code == 200:
            bot.send_message(message.chat.id, f"✅ SMS kodi yuborildi!\nRequest ID: {request_id}")
        else:
            bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi\nStatus Code: {response.status_code}\nResponse: {response.text}")

# Botni ishga tushirish
bot.polling(none_stop=True)
