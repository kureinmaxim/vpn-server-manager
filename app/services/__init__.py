class ServiceRegistry:
    """Реестр сервисов для Dependency Injection"""
    _services = {}
    
    @classmethod
    def register(cls, name: str, service):
        """Регистрация сервиса"""
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str):
        """Получение сервиса по имени"""
        return cls._services.get(name)
    
    @classmethod
    def clear(cls):
        """Очистка реестра (для тестов)"""
        cls._services.clear()

# Инициализация реестра
registry = ServiceRegistry()
