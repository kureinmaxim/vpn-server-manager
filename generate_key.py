from cryptography.fernet import Fernet

def generate_key():
    """Генерирует ключ и сохраняет его в файл .env."""
    key = Fernet.generate_key()
    with open(".env", "wb") as key_file:
        key_file.write(b"SECRET_KEY=" + key)
    print("Ключ успешно сгенерирован и сохранен в .env файле.")
    print("ВАЖНО: Если вы перезаписали существующий ключ, перезапустите сервер и пересоздайте записи с паролями.")

if __name__ == "__main__":
    generate_key() 