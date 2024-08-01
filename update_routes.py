import paramiko
import os
import time

USERNAME = os.getenv("KEENETIC_USERNAME", "admin")
PASSWORD = os.getenv("KEENETIC_PASSWORD", None)
KEENETIC_HOST = os.getenv("KEENETIC_HOST", "192.168.0.1")
KEENETIC_PORT = os.getenv("KEENETIC_PORT", 22)
KEENTIC_INTERFACE = os.getenv("KEENTIC_INTERFACE", "Proxy0")

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
    ip, prefix_length = cidr.split("/")
    prefix_length = int(prefix_length)
    mask = (0xFFFFFFFF >> (32 - prefix_length)) << (32 - prefix_length)
    netmask = ".".join([str((mask >> (i * 8)) & 0xFF) for i in range(4)[::-1]])
    return ip, netmask


def fetch_cidr_list(url):
    import requests

    response = requests.get(url)
    response.raise_for_status()
    return response.text.splitlines()


def execute_command(ssh, command, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            stdin, stdout, stderr = ssh.exec_command(command)
            error = stderr.read()
            if error:
                print(f"Ошибка: {error.decode()}")
            return stdout.read().decode()
        except paramiko.SSHException as e:
            if "Channel closed" in str(e):
                print(f"Channel closed detected. Retrying... ({attempt + 1}/{retries})")
                attempt += 1
                time.sleep(1)
            else:
                raise e
    raise Exception(f"Failed to execute command after {retries} attempts: {command}")


def add_routes_via_ssh(routes):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("Connecting to Keenetic")
        ssh.connect(
            KEENETIC_HOST, port=KEENETIC_PORT, username=USERNAME, password=PASSWORD
        )
        print("Connected")

        for ip, netmask in routes:
            print(f"Добавление маршрута: {ip} {netmask}")
            command = f"no ip route {ip} {netmask}"
            execute_command(ssh, command)
            command = f"ip route {ip} {netmask} {KEENTIC_INTERFACE}"
            execute_command(ssh, command)

        print("Все маршруты добавлены.")
    except Exception as e:
        print(f"Ошибка при подключении или выполнении команд: {e}")
    finally:
        ssh.close()


def main():
    url = "https://antifilter.download/list/allyouneed.lst"

    try:
        cidr_list = fetch_cidr_list(url)
        cidr_list.extend(CUSTOM_CIDR_LIST)

        routes_to_add = []

        for cidr in cidr_list:
            if cidr.strip():
                ip, netmask = cidr_to_netmask(cidr.strip())
                routes_to_add.append((ip, netmask))

        add_routes_via_ssh(routes_to_add)
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
