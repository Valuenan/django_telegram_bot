import hmac
import hashlib
import json
from urllib.parse import parse_qsl


def verify_telegram_data(init_data: str, bot_token: str):
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_received = parsed_data.pop('hash', None)
        if not hash_received:
            return None

        # Сортируем ключи по алфавиту и соединяем через \n
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # Вычисляем секретный ключ (HMAC-SHA256 от токена с солью "WebAppData")
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()

        # Вычисляем финальный хеш
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if calculated_hash == hash_received:
            user_json = parsed_data.get('user')
            return json.loads(user_json) if user_json else None

        return None
    except Exception as e:
        print(f"Validation Error: {e}")
        return None