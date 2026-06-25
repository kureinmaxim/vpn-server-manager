#!/usr/bin/env python3
"""rotate_secret_key.py — безопасная ротация SECRET_KEY (Fernet).

Зачем: если SECRET_KEY скомпрометирован (попал в git/историю), его нужно сменить.
Данные шифруются Fernet'ом в ДВА слоя (как в app/services/data_manager_service.py):
  1) отдельные поля-секреты (пароли/логины) — сырой Fernet-токен (строка с 'gAAAAA');
  2) весь файл данных целиком — тоже сырой Fernet-токен.
Скрипт перешифровывает оба слоя со старого ключа на новый, сохраняя структуру.

Делает:
  1. читает старый SECRET_KEY из .env;
  2. расшифровывает файл данных и все поля-токены старым ключом;
  3. генерирует новый ключ, перешифровывает поля и весь файл новым ключом;
  4. делает бэкап .env и файла данных (timestamped) и записывает новый ключ/файл.

Запуск из корня проекта:
  python scripts/rotate_secret_key.py --dry-run   # показать план, ничего не менять
  python scripts/rotate_secret_key.py             # выполнить ротацию (с бэкапом)
  python scripts/rotate_secret_key.py --data-file data/servers.json.enc
"""
import argparse
import json
import os
import shutil
import sys
import time

from cryptography.fernet import Fernet, InvalidToken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PREFIX = "gAAAAA"  # префикс Fernet-токена (как проверяет data_manager_service)


def find_data_file(explicit):
    if explicit:
        return explicit if os.path.isabs(explicit) else os.path.join(ROOT, explicit)
    cfg = os.path.join(ROOT, "config.json")
    if os.path.isfile(cfg):
        try:
            adf = (json.load(open(cfg, encoding="utf-8")) or {}).get("active_data_file")
            if adf:
                return adf if os.path.isabs(adf) else os.path.join(ROOT, adf)
        except Exception:
            pass
    return os.path.join(ROOT, "data", "servers.json.enc")


def reencrypt(node, old, new, stats):
    """Рекурсивно перешифровать все строки-Fernet-токены (поля) старый→новый."""
    if isinstance(node, dict):
        return {k: reencrypt(v, old, new, stats) for k, v in node.items()}
    if isinstance(node, list):
        return [reencrypt(v, old, new, stats) for v in node]
    if isinstance(node, str) and node.startswith(TOKEN_PREFIX):
        try:
            plain = old.decrypt(node.encode())
        except InvalidToken:
            stats["skipped"] += 1
            return node
        stats["fields"] += 1
        return new.encrypt(plain).decode()
    return node


def main():
    ap = argparse.ArgumentParser(description="Ротация SECRET_KEY (Fernet)")
    ap.add_argument("--data-file", help="путь к *.enc (по умолчанию из config.json / data/)")
    ap.add_argument("--dry-run", action="store_true", help="показать план без изменений")
    args = ap.parse_args()

    env_path = os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        print("❌ .env не найден в корне проекта")
        return 1
    env_lines = open(env_path, encoding="utf-8").read().splitlines()
    old_key = next((l.split("=", 1)[1].strip() for l in env_lines
                    if l.startswith("SECRET_KEY=")), None)
    if not old_key:
        print("❌ SECRET_KEY не найден в .env")
        return 1
    try:
        old = Fernet(old_key.encode())
    except Exception as e:
        print(f"❌ Старый ключ невалиден как Fernet: {e}")
        return 1

    data_file = find_data_file(args.data_file)
    if not os.path.isfile(data_file):
        print(f"❌ Файл данных не найден: {data_file}")
        return 1
    blob = open(data_file, "rb").read()
    try:
        data = json.loads(old.decrypt(blob).decode("utf-8")) if blob.strip() else []
    except Exception as e:
        print(f"❌ Не удалось расшифровать {data_file} старым ключом: {e}")
        print("   Проверь, что .env содержит ВЕРНЫЙ текущий ключ для этого файла.")
        return 1

    new_key = Fernet.generate_key().decode()
    new = Fernet(new_key.encode())
    stats = {"fields": 0, "skipped": 0}
    new_data = reencrypt(data, old, new, stats)
    new_blob = new.encrypt(json.dumps(new_data, ensure_ascii=False).encode("utf-8"))

    print(f"Файл данных          : {data_file}")
    print(f"Полей перешифровано  : {stats['fields']}  (пропущено битых: {stats['skipped']})")
    print(f"Старый SECRET_KEY    : {old_key}")
    print(f"Новый  SECRET_KEY    : {new_key}")

    if args.dry_run:
        print("\n[dry-run] Ничего не записано (бэкап не делался). "
              "Убери --dry-run, чтобы применить.")
        return 0

    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(env_path, f"{env_path}.bak-{ts}")
    shutil.copy2(data_file, f"{data_file}.bak-{ts}")

    with open(data_file, "wb") as f:
        f.write(new_blob)

    out, replaced = [], False
    for l in env_lines:
        if l.startswith("SECRET_KEY="):
            out.append(f"SECRET_KEY={new_key}")
            replaced = True
        else:
            out.append(l)
    if not replaced:
        out.append(f"SECRET_KEY={new_key}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print(f"\n✅ Ротация выполнена. Бэкапы:")
    print(f"   {env_path}.bak-{ts}")
    print(f"   {data_file}.bak-{ts}")
    print("   Перезапусти приложение и проверь, что данные читаются. "
          "Затем удали бэкапы (в них старый ключ!).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
