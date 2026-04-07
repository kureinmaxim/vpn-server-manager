.PHONY: help install install-dev test test-cov lint format clean run run-desktop build dist

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

install-dev: ## Установить зависимости для разработки
	pip install -r requirements.txt
	pip install -e .[dev,build]

test: ## Запустить тесты
	pytest

test-cov: ## Запустить тесты с покрытием
	pytest --cov=app --cov-report=html --cov-report=term

lint: ## Проверить код линтерами
	flake8 app tests
	bandit -r app

format: ## Форматировать код
	black app tests
	isort app tests

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage

run: ## Запустить приложение в web режиме
	python run.py

run-desktop: ## Запустить приложение в desktop режиме
	python run.py --desktop

run-debug: ## Запустить приложение в debug режиме
	python run.py --debug

run-desktop-debug: ## Запустить desktop приложение в debug режиме
	python run.py --desktop --debug

build: ## Собрать приложение
	pyinstaller --clean VPNServerManager-Clean.spec

dist: ## Создать дистрибутив
	python build_macos.py

setup-env: ## Настроить окружение
	cp env.example .env
	@echo "Отредактируйте .env файл с вашими настройками"

init-translations: ## Инициализировать переводы
	pybabel extract -F babel.cfg -o messages.pot .
	pybabel init -i messages.pot -d translations -l en
	pybabel init -i messages.pot -d translations -l ru
	pybabel init -i messages.pot -d translations -l zh

update-translations: ## Обновить переводы
	pybabel extract -F babel.cfg -o messages.pot .
	pybabel update -i messages.pot -d translations

compile-translations: ## Скомпилировать переводы
	pybabel compile -d translations

check-security: ## Проверить безопасность
	bandit -r app -f json -o security-report.json
	@echo "Отчет о безопасности сохранен в security-report.json"

docker-build: ## Собрать Docker образ
	docker build -t vpn-manager-clean .

docker-run: ## Запустить в Docker (порт 5000:5000)
	docker run -p 5000:5000 vpn-manager-clean

docker-run-custom: ## Запустить в Docker с кастомным портом (make docker-run-custom PORT=5001)
	@PORT=$${PORT:-5000}; \
	echo "🐳 Запуск контейнера на порту $$PORT"; \
	docker run -p $$PORT:5000 -e PORT=5000 vpn-manager-clean

docker-run-multi: ## Запустить несколько контейнеров (порты 5000, 5001, 5002)
	@echo "🚀 Запуск 3 экземпляров Docker контейнеров..."
	docker run -d -p 5000:5000 --name vpn-manager-1 vpn-manager-clean
	docker run -d -p 5001:5000 --name vpn-manager-2 vpn-manager-clean
	docker run -d -p 5002:5000 --name vpn-manager-3 vpn-manager-clean
	@echo "✅ Запущено 3 контейнера:"
	@echo "   📡 http://localhost:5000 (vpn-manager-1)"
	@echo "   📡 http://localhost:5001 (vpn-manager-2)"
	@echo "   📡 http://localhost:5002 (vpn-manager-3)"

docker-stop-multi: ## Остановить все запущенные контейнеры
	@echo "⏹️  Остановка контейнеров..."
	-docker stop vpn-manager-1 vpn-manager-2 vpn-manager-3 2>/dev/null
	-docker rm vpn-manager-1 vpn-manager-2 vpn-manager-3 2>/dev/null
	@echo "✅ Все контейнеры остановлены"

version: ## Показать текущую версию из config.json
	@python3 -c "import json; config = json.load(open('config.json')); print(f\"VPN Server Manager v{config['app_info']['version']}\")"

all: clean install-dev test lint format ## Выполнить все проверки
