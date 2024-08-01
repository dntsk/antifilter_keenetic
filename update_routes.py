#!/usr/bin/env python3

import urllib.request
import urllib.parse
import base64
import time
import os

USERNAME = os.getenv("KEENETIC_USERNAME", "admin")
PASSWORD = os.getenv("KEENETIC_PASSWORD", None)
KEENETIC_HOST = os.getenv("KEENETIC_HOST", "192.168.0.1")
INTERFACE = os.getenv("KEENETIC_INTERFACE", "Proxy0")

CUSTOM_CIDR_LIST = [
    # Youtube
    "64.18.0.0/20",
    "64.233.160.0/19",
    "66.102.0.0/20",
    "66.249.80.0/20",
    "72.14.192.0/18",
    "74.125.0.0/16",
    "173.194.0.0/16",
    "207.126.144.0/20",
    "209.85.128.0/17",
    "216.58.208.0/20",
    "216.239.32.0/19",
    "213.0.0.0/8",
]


def cidr_to_netmask(cidr):
    """Преобразует префикс CIDR в маску подсети."""
    try:
        ip, prefix_length = cidr.split("/")
        prefix_length = int(prefix_length)

        # Создаем маску подсети из префикса
        mask = (0xFFFFFFFF >> (32 - prefix_length)) << (32 - prefix_length)
        netmask = ".".join([str((mask >> (i * 8)) & 0xFF) for i in range(4)[::-1]])

        return ip, netmask
    except ValueError:
        raise ValueError("Неверный формат CIDR")


def fetch_cidr_list(url):
    """Загружает список CIDR из указанного URL."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode().splitlines()


def add_route_to_keenetic(ip, netmask, gateway, username, password):
    """Добавляет маршрут на роутер Keenetic с использованием GET-запроса."""
    url = f"http://{KEENETIC_HOST}/cgi-bin/luci/admin/network/routes"
    params = {"ip": ip, "mask": netmask, "gateway": gateway, "interface": INTERFACE}

    # Кодируем параметры для URL
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    # Создаем запрос
    request = urllib.request.Request(full_url)
    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    # Аутентификация
    credentials = f"{username}:{password}"
    base64_credentials = base64.b64encode(credentials.encode()).decode()
    request.add_header("Authorization", f"Basic {base64_credentials}")

    # Отправка запроса
    try:
        with urllib.request.urlopen(request) as response:
            print(f"Маршрут {ip} с маской {netmask} успешно добавлен.")
            return True
    except Exception as e:
        print(f"Ошибка при добавлении маршрута {ip}: {e}")
        return False


def add_routes_to_keenetic(routes, gateway, username, password, max_retries=3):
    """Добавляет маршруты на роутер Keenetic с повторными попытками."""
    for route in routes:
        ip, netmask = route
        success = False
        attempts = 0

        while not success and attempts < max_retries:
            success = add_route_to_keenetic(ip, netmask, gateway, username, password)
            if not success:
                attempts += 1
                print(f"Попытка {attempts} для маршрута {ip}.")
                time.sleep(2)  # Задержка перед повторной попыткой


def main():
    url = "https://antifilter.download/list/allyouneed.lst"
    if PASSWORD is None:
        print(
            "Для использования данного скрипта необходимо установить переменные окружения KEENETIC_USERNAME и KEENETIC_PASSWORD."
        )
        return

    try:
        cidr_list = fetch_cidr_list(url)
        cidr_list.extend(CUSTOM_CIDR_LIST)
        routes_to_add = []

        # Генерируем маршруты
        for cidr in cidr_list:
            if cidr.strip():  # Проверяем, что строка не пустая
                ip, netmask = cidr_to_netmask(cidr.strip())
                routes_to_add.append((ip, netmask))

        # Добавляем маршруты пачками
        add_routes_to_keenetic(routes_to_add, KEENETIC_HOST, USERNAME, PASSWORD)
    except Exception as e:
        print(f"Ошибка: {e}")


# Пример использования
if __name__ == "__main__":
    main()
