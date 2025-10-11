import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional, Any
import logging
from ..exceptions import APIError

logger = logging.getLogger(__name__)

class APIService:
    """Сервис для работы с внешними API"""
    
    def __init__(self, base_url: str = '', timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Создание сессии с retry-логикой"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Устанавливаем заголовки по умолчанию
        session.headers.update({
            'User-Agent': 'VPNServerManager-Clean/3.7.3',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        return session
    
    def get(self, endpoint: str = '', params: Optional[Dict] = None, 
            headers: Optional[Dict] = None) -> Dict[str, Any]:
        """GET запрос"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        
        try:
            logger.info(f"Making GET request to: {url}")
            response = self.session.get(
                url, 
                params=params, 
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Пытаемся получить JSON, если не получается - возвращаем текст
            try:
                return response.json()
            except ValueError:
                return {'data': response.text}
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {url}: {str(e)}")
            raise APIError(f"Request timeout: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {str(e)}")
            raise APIError(f"Connection error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {str(e)}")
            raise APIError(f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            raise APIError(f"Request failed: {str(e)}")
    
    def post(self, endpoint: str = '', data: Optional[Dict] = None, 
             json: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """POST запрос"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        
        try:
            logger.info(f"Making POST request to: {url}")
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            try:
                return response.json()
            except ValueError:
                return {'data': response.text}
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {url}: {str(e)}")
            raise APIError(f"Request timeout: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {str(e)}")
            raise APIError(f"Connection error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {str(e)}")
            raise APIError(f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            raise APIError(f"Request failed: {str(e)}")
    
    def check_ip_info(self, ip: str) -> Dict[str, Any]:
        """Проверка информации об IP адресе"""
        try:
            url = f"https://ipinfo.io/{ip}/json"
            logger.info(f"Checking IP info for: {ip}")
            return self.get(url)
        except Exception as e:
            logger.error(f"Error checking IP info for {ip}: {str(e)}")
            raise APIError(f"IP info check failed: {str(e)}")
    
    def get_current_ip(self) -> str:
        """Получение текущего IP адреса"""
        try:
            # Пробуем несколько сервисов
            services = [
                "https://ipinfo.io/ip",
                "https://api.ipify.org",
                "https://icanhazip.com"
            ]
            
            for service in services:
                try:
                    response = self.get(service)
                    ip = response.get('data', '').strip() if isinstance(response, dict) else str(response).strip()
                    if ip and self._is_valid_ip(ip):
                        logger.info(f"Current IP obtained from {service}: {ip}")
                        return ip
                except Exception as e:
                    logger.warning(f"Failed to get IP from {service}: {str(e)}")
                    continue
            
            raise APIError("Unable to determine current IP address")
            
        except Exception as e:
            logger.error(f"Error getting current IP: {str(e)}")
            raise APIError(f"Current IP check failed: {str(e)}")
    
    def test_dns_leak(self) -> Dict[str, Any]:
        """Тест на утечку DNS"""
        try:
            # Это упрощенная версия - в реальном приложении может потребоваться более сложная логика
            url = "https://dnsleaktest.com/api/v1/dnsleak"
            return self.get(url)
        except Exception as e:
            logger.error(f"DNS leak test failed: {str(e)}")
            raise APIError(f"DNS leak test failed: {str(e)}")
    
    def test_connection_speed(self, test_url: str = "https://httpbin.org/bytes/1048576") -> Dict[str, Any]:
        """Тест скорости соединения"""
        try:
            import time
            
            start_time = time.time()
            response = self.get(test_url)
            end_time = time.time()
            
            duration = end_time - start_time
            # Предполагаем размер 1MB для тестового файла
            size_mb = 1
            speed_mbps = (size_mb * 8) / duration  # Конвертируем в Mbps
            
            return {
                'duration': duration,
                'speed_mbps': speed_mbps,
                'size_mb': size_mb
            }
        except Exception as e:
            logger.error(f"Connection speed test failed: {str(e)}")
            raise APIError(f"Connection speed test failed: {str(e)}")
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Простая валидация IP адреса"""
        import re
        pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        return bool(re.match(pattern, ip))
    
    def close(self):
        """Закрытие сессии"""
        if self.session:
            self.session.close()
            logger.info("API service session closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
