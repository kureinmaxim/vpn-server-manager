"""
Rate Limiter для защиты от слишком частых запросов
"""
import time
import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, max_requests=10, time_window=60):
        """
        Args:
            max_requests: максимум запросов
            time_window: в течение скольких секунд
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        self.blocked_count = defaultdict(int)  # Счетчик блокировок
        self.lock = Lock()
    
    def is_allowed(self, key):
        """
        Проверить можно ли выполнить запрос
        
        Args:
            key: уникальный идентификатор (например server_id)
            
        Returns:
            bool: True если запрос разрешен, False если превышен лимит
        """
        with self.lock:
            now = time.time()
            
            # Удаляем старые запросы (за пределами окна)
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.time_window
            ]
            
            # Проверяем лимит
            if len(self.requests[key]) >= self.max_requests:
                self.blocked_count[key] += 1
                
                # Логируем каждую 10-ю блокировку
                if self.blocked_count[key] % 10 == 0:
                    logger.warning(
                        f"🚫 Rate limit exceeded for '{key}' - "
                        f"blocked {self.blocked_count[key]} times "
                        f"(limit: {self.max_requests} req/{self.time_window}s)"
                    )
                
                return False
            
            # Добавляем новый запрос
            self.requests[key].append(now)
            return True
    
    def get_remaining(self, key):
        """Получить количество оставшихся запросов"""
        with self.lock:
            now = time.time()
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.time_window
            ]
            return max(0, self.max_requests - len(self.requests[key]))

