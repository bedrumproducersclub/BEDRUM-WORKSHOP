import os

def get_event_caption():
    event_title = os.getenv("EVENT_TITLE", "Событие")
    event_date = os.getenv("EVENT_DATE", "Дата не указана")
    event_city = os.getenv("EVENT_CITY", "Город не указан")
    price_text = os.getenv("PRICE_TEXT", "Стоимость не указана")
    payment_text = os.getenv("PAYMENT_TEXT", "")

    return f"*{event_title}*\n📅 {event_date}\n📍 {event_city}\n\n{price_text}\n\n{payment_text}"
