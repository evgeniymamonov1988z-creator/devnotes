# -*- coding: utf-8 -*-
"""
Модуль синхронизации с Google Drive.

Использует папку Google Drive на компьютере (Google Drive for Desktop).
Файлы автоматически синхронизируются с облаком.

Настройка:
1. Убедись, что Google Drive for Desktop установлен
2. Укажи путь к папке "Мой диск" (обычно G:\\Мой диск)
3. Готово! Файлы будут копироваться в эту папку
"""

import os
import shutil
import datetime
import threading

# Путь к Google Drive на компьютере
GOOGLE_DRIVE_PATH = r"G:\Мой диск\MAMONOV\DevNotes"

# Имя файла на Google Drive
BACKUP_FILENAME = "project_notes.json"


def ensure_drive_folder():
    """Создаёт папку на Google Drive, если её нет."""
    try:
        os.makedirs(GOOGLE_DRIVE_PATH, exist_ok=True)
        return True
    except Exception as e:
        print(f"Ошибка создания папки: {e}")
        return False


def sync_to_drive(data_file, filename=None):
    """
    Копирование файла в папку Google Drive.
    Возвращает (success: bool, message: str)
    """
    if not os.path.exists(data_file):
        return False, f"Файл не найден: {data_file}"

    if not ensure_drive_folder():
        return False, "Не удалось создать папку на Google Drive"

    dest = os.path.join(GOOGLE_DRIVE_PATH, filename or BACKUP_FILENAME)

    try:
        # Копируем файл
        shutil.copy2(data_file, dest)

        # Создаём резервную копию с датой
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"project_notes_{timestamp}.json"
        backup_path = os.path.join(GOOGLE_DRIVE_PATH, backup_name)
        shutil.copy2(data_file, backup_path)

        return True, f"Синхронизировано с Google Drive ({GOOGLE_DRIVE_PATH})"
    except Exception as e:
        return False, f"Ошибка синхронизации: {str(e)}"


def sync_from_drive(data_file, filename=None):
    """
    Копирование файла из папки Google Drive.
    Возвращает (success: bool, message: str)
    """
    src = os.path.join(GOOGLE_DRIVE_PATH, filename or BACKUP_FILENAME)

    if not os.path.exists(src):
        return False, "Файл не найден на Google Drive"

    try:
        # Копируем файл обратно
        shutil.copy2(src, data_file)
        return True, "Синхронизировано с Google Drive"
    except Exception as e:
        return False, f"Ошибка синхронизации: {str(e)}"


def list_backups():
    """Список всех резервных копий на Google Drive."""
    if not os.path.exists(GOOGLE_DRIVE_PATH):
        return []

    backups = []
    for f in os.listdir(GOOGLE_DRIVE_PATH):
        if f.startswith("project_notes_") and f.endswith(".json"):
            full_path = os.path.join(GOOGLE_DRIVE_PATH, f)
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
            backups.append((f, mod_time))

    backups.sort(key=lambda x: x[1], reverse=True)
    return backups


# ---------------------------------------------------------------------------
# Для тестирования
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Тест модуля Google Drive синхронизации")
    print("=" * 50)
    print(f"Путь к Google Drive: {GOOGLE_DRIVE_PATH}")
    print(f"Папка существует: {os.path.exists(GOOGLE_DRIVE_PATH)}")

    # Тест синхронизации
    test_file = os.path.join(os.path.dirname(__file__), "project_notes_backup.json")
    if os.path.exists(test_file):
        success, msg = sync_to_drive(test_file)
        print(f"Результат: {msg}")

        # Список бэкапов
        backups = list_backups()
        print(f"\nРезервные копии на Google Drive:")
        for name, time in backups[:5]:
            print(f"  {name} — {time.strftime('%d.%m.%Y %H:%M')}")
