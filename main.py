
import imaplib
import smtplib
import email
import time
import asyncio
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv


# 🔹 Доступ к почте
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

# Загружаем переменные из .env
load_dotenv()
# Читаем переменные
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

from g4f.client import Client
client = Client()



def get_latest_email(mail):
    mail.select("inbox")
    _, data = mail.search(None, "UNSEEN")  # Только непрочитанные письма
    mail_ids = data[0].split()

    if not mail_ids:
        return None, None, None
        
    latest_email_id = mail_ids[-1]  # Берём последнее письмо
    _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    sender = msg["From"]
    subject = msg["Subject"]
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8")
    else:
        body = msg.get_payload(decode=True).decode("utf-8")
        
    mail.store(latest_email_id, "+FLAGS", "\\Seen")  # Помечаем как прочитанное


    return sender, subject, body.strip()



def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["From"] = EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
            server.login(EMAIL, PASSWORD)
            server.sendmail(EMAIL, to_email, msg.as_string())
            return True
    except Exception as e:
        print("Error sending email:", e)
        return False


async def get_g4f_response_async(prompt, timeout=20):
    collected_response = ""
    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            web_search=True,
            stream=True  # Потоковый вывод
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                collected_response += chunk.choices[0].delta.content
            
            if time.time() - start_time > timeout:
                collected_response += " [Ответ обрезан по таймауту]"
                break

    except Exception as e:
        collected_response = f"Ошибка при генерации ответа: {str(e)}"

    return collected_response.strip() if collected_response else "Ответ не получен"

def get_g4f_response(prompt):
    return asyncio.run(get_g4f_response_async(prompt))

def check_and_reply(mail):
    try:
        sender, subject, question = get_latest_email(mail)
    except Exception as e:
        print('Ошибка')
        return None
    if sender and question:
        print(f"📩 Новое письмо от {sender}, тема: {subject}, текст: {question}")
        
        response = get_g4f_response(question)
        print(f"✅ Ответ сформирован: {response}")

        send_email(sender, f"Re: {subject}", response)
        print(f"📨 Ответ отправлен: {response}")


def wait_for_email():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    while True:
        print("⏳ Проверяем новые письма...")
        check_and_reply(mail)  # Функция для обработки новых писем
        time.sleep(10)  # Ждём 30 секунд перед следующей проверкой


# 📌 Запуск бота
wait_for_email()