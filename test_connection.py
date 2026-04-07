import requests
import socket
import time

def test_socket_connection():
    """Проверяет соединение через сокеты."""
    servers = [
        ("8.8.8.8", 53),  # Google DNS
        ("1.1.1.1", 53),  # Cloudflare DNS
        ("208.67.222.222", 53)  # OpenDNS
    ]
    
    for server, port in servers:
        try:
            print(f"Проверка соединения с {server}:{port}...")
            start_time = time.time()
            socket.create_connection((server, port), timeout=1)
            elapsed = time.time() - start_time
            print(f"✅ Соединение с {server}:{port} успешно (время: {elapsed:.3f} сек)")
            return True
        except Exception as e:
            print(f"❌ Не удалось подключиться к {server}:{port}: {e}")
    
    return False

def test_http_connection():
    """Проверяет соединение через HTTP-запросы."""
    urls = [
        "https://www.google.com",
        "https://www.example.com",
        "https://www.cloudflare.com"
    ]
    
    for url in urls:
        try:
            print(f"Проверка HTTPS-запроса к {url}...")
            start_time = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start_time
            print(f"✅ HTTPS-запрос к {url} успешен, статус: {response.status_code} (время: {elapsed:.3f} сек)")
            return True
        except Exception as e:
            print(f"❌ Ошибка HTTPS-запроса к {url}: {e}")
    
    # Если HTTPS не работает, пробуем HTTP
    http_urls = [
        "http://www.google.com",
        "http://www.example.com",
        "http://www.cloudflare.com"
    ]
    
    for url in http_urls:
        try:
            print(f"Проверка HTTP-запроса к {url}...")
            start_time = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start_time
            print(f"✅ HTTP-запрос к {url} успешен, статус: {response.status_code} (время: {elapsed:.3f} сек)")
            return True
        except Exception as e:
            print(f"❌ Ошибка HTTP-запроса к {url}: {e}")
    
    return False

if __name__ == "__main__":
    print("=== Тестирование соединения с интернетом ===")
    
    socket_ok = test_socket_connection()
    print("\n")
    http_ok = test_http_connection()
    
    print("\n=== Результаты тестирования ===")
    print(f"Соединение через сокеты: {'✅ УСПЕШНО' if socket_ok else '❌ ОШИБКА'}")
    print(f"HTTP/HTTPS-запросы: {'✅ УСПЕШНО' if http_ok else '❌ ОШИБКА'}")
    print(f"Итоговый статус: {'✅ ИНТЕРНЕТ ДОСТУПЕН' if (socket_ok or http_ok) else '❌ ИНТЕРНЕТ НЕДОСТУПЕН'}")
