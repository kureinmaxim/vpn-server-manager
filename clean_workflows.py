#!/usr/bin/env python3
"""
Скрипт для очистки старых workflow runs в GitHub Actions
"""

import os
import requests
import json
from datetime import datetime, timedelta

def clean_workflow_runs():
    """Очищает старые workflow runs"""
    
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
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # URL для получения workflow runs
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs"
    
    try:
        # Получаем список workflow runs
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        runs = response.json()['workflow_runs']
        print(f"📊 Найдено {len(runs)} workflow runs")
        
        # Фильтруем только неудачные runs старше 1 часа
        cutoff_time = datetime.now() - timedelta(hours=1)
        failed_runs = []
        
        for run in runs:
            if run['conclusion'] == 'failure':
                created_at = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                if created_at < cutoff_time:
                    failed_runs.append(run)
        
        print(f"🗑️ Найдено {len(failed_runs)} старых неудачных runs для удаления")
        
        # Удаляем старые неудачные runs
        deleted_count = 0
        for run in failed_runs:
            delete_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run['id']}"
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code == 204:
                print(f"✅ Удален run #{run['id']} ({run['name']})")
                deleted_count += 1
            else:
                print(f"❌ Ошибка удаления run #{run['id']}: {delete_response.status_code}")
        
        print(f"🎉 Удалено {deleted_count} старых workflow runs")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка API: {e}")
    except KeyError as e:
        print(f"❌ Ошибка парсинга ответа: {e}")

if __name__ == "__main__":
    print("🧹 Очистка старых workflow runs...")
    clean_workflow_runs() 