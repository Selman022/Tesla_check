import time
import random
import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot
from dotenv import load_dotenv
import os

# Render ortamında .env dosyasını bu path'ten yükle
load_dotenv("/etc/secrets/.env")

# Telegram ayarları
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DATA_FILE = "tesla_vehicles.json"


def load_existing_ids():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f).get("ids", [])
    except FileNotFoundError:
        return []


def save_new_ids(vehicles):
    with open(DATA_FILE, "w") as f:
        json.dump({"last_updated": str(datetime.now()), "ids": [v["data_id"][:8] for v in vehicles]}, f)


def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("✅ Telegram mesajı gönderildi.")
    except Exception as e:
        print(f"⚠ Telegram mesajı gönderilemedi: {str(e)}")


def get_current_vehicles():
    url = "https://www.tesla.com/tr_TR/inventory/new/my"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"⚠ HTTP hata: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.select("main article.result.card")
    vehicles = []

    for article in articles:
        try:
            data_id = article.get("data-id")
            model_name = article.select_one("h3.tds-text--h4 span").text.strip()

            if "Model Y" not in model_name:
                continue

            configuration = article.select_one("div.tds-text_color--10").text.strip()
            stock_status = article.find(lambda tag: tag.name == "div" and tag.get("class") is None and "-" in tag.text).text.strip()
            price = article.select_one("span.result-purchase-price.tds-text--h4").text.strip()

            vehicles.append({
                "data_id": data_id,
                "model_name": model_name,
                "configuration": configuration,
                "stock_status": stock_status,
                "price": price
            })
        except Exception as e:
            print(f"⚠ DATA ID: {data_id[:8]} için bilgi çekilemedi: {str(e)}")
            continue

    return vehicles


def compare_and_alert(new_vehicles, existing_ids):
    new_vehicles_list = [v for v in new_vehicles if v["data_id"][:8] not in existing_ids]

    if new_vehicles_list:
        print(f"🚨 YENİ ARAÇLAR BULUNDU ({len(new_vehicles_list)} adet):")
        message = f"🚨 Yeni Tesla Model Y Bulundu! ({len(new_vehicles_list)} adet)\n\n"

        for vehicle in new_vehicles_list:
            vehicle_info = (
                f"DATA ID: {vehicle['data_id'][:8]}\n"
                f"Model Adı: {vehicle['model_name']}\n"
                f"Konfigürasyon: {vehicle['configuration']}\n"
                f"Stok Durumu: {vehicle['stock_status']}\n"
                f"Fiyat: {vehicle['price']}\n"
            )
            print(vehicle_info)
            message += vehicle_info + "\n"

        send_telegram_message(message)
    else:
        print("ℹ️ Yeni araç bulunamadı.")


def main():
    existing_ids = load_existing_ids()
    current_vehicles = get_current_vehicles()

    if current_vehicles:
        print(f"✅ Bulunan araç sayısı: {len(current_vehicles)}")

    compare_and_alert(current_vehicles, existing_ids)
    save_new_ids(current_vehicles)


if __name__ == "__main__":
    main()

while True:
    main()
    time.sleep(3600 + random.randint(0, 300))  # Her saat + biraz rastgele gecikme