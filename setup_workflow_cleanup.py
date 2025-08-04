#!/usr/bin/env python3
"""
Скрипт для настройки автоматической очистки workflow runs
"""

import os
import requests
import json

def setup_workflow_cleanup():
    """Настраивает автоматическую очистку workflow runs"""
    
    # Настройки
    repo_owner = "kureinmaxim"
    repo_name = "vpn-server-manager"
    
    # Получите токен из переменной окружения
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ Ошибка: Установите переменную GITHUB_TOKEN")
        print("Пример: export GITHUB_TOKEN=your_token_here")
        return
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    # Настройки очистки
    cleanup_settings = {
        "enabled": True,
        "retention_days": 1,  # Хранить только 1 день
        "limit": 1  # Максимум 1 workflow run
    }
    
    try:
        # Применяем настройки для всех workflow
        workflows_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows"
        response = requests.get(workflows_url, headers=headers)
        response.raise_for_status()
        
        workflows = response.json()['workflows']
        print(f"📋 Найдено {len(workflows)} workflows")
        
        for workflow in workflows:
            workflow_id = workflow['id']
            workflow_name = workflow['name']
            
            # URL для настройки очистки
            cleanup_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}/timing"
            
            cleanup_response = requests.put(cleanup_url, headers=headers, json=cleanup_settings)
            
            if cleanup_response.status_code == 200:
                print(f"✅ Настроена очистка для workflow: {workflow_name}")
            else:
                print(f"❌ Ошибка настройки очистки для {workflow_name}: {cleanup_response.status_code}")
        
        print("🎉 Настройка автоматической очистки завершена!")
        print("📝 Теперь старые workflow runs будут автоматически удаляться через 1 день")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка API: {e}")
    except KeyError as e:
        print(f"❌ Ошибка парсинга ответа: {e}")

if __name__ == "__main__":
    print("⚙️ Настройка автоматической очистки workflow runs...")
    setup_workflow_cleanup() 