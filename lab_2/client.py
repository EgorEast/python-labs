import argparse
# Стандартный модуль argparse.
# Подробнее: https://docs.python.org/3/library/argparse.html
import socket
# Стандартный модуль socket.
# Подробнее: https://docs.python.org/3/library/socket.html
import sys
# Стандартный модуль sys.
# Подробнее: https://docs.python.org/3/library/sys.html
import time
# Стандартный модуль time.
# Подробнее: https://docs.python.org/3/library/time.html
import json
# Стандартный модуль json.
# Подробнее: https://docs.python.org/3/library/json.html

import threading

# Стандартный модуль threading.
# Подробнее: https://docs.python.org/3/library/threading.html

# Глобальная переменная, отвечающая за остановку клиента.
shutdown = False


class Message:
    """
    Класс-Сообщение. Представляет сообщения,
    которые будут приходить от клиентов.
    """

    def __init__(self, **data):
        # Устанавливаем дополнительные атрибуты сообщения.
        self.status = 'online'
        # Распаковываем кортеж именованных аргументов в параметры класса.
        # Паттерн Builder
        for param, value in data.items():
            setattr(self, param, value)

        # время получения сообщения.
        self.curr_time = time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime())

    def to_json(self):
        """
        Возвращает атрибуты класса и их значения в виде json.
        Использует стандартный модуль python - json.
        """
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class P2PClient:
    """
    Класс с "бизнес-логикой" p2p клиента.
    """

    def __init__(self, host:str, port:int, name:str|None=None):
        # Атрибут для хранения текущего соединения:
        self.current_connection = None
        # Атрибут для хранения адреса текущего клиента
        self.client_address = (host, port)

        # Если имя не задано, то в качестве имени сохраняем адрес клиента:
        if name is None:
            self.name = f"{host[0]}:{port[1]}"
        else:
            self.name = name
        # Создаем сокет:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Запускаем "прослушивание" указанного адреса:
        self.socket.bind(self.client_address)

    def receive(self):
        """
        Получает сообщение из сокета и выводит полученное сообщение
        в стандартный поток вывода (консоль)
        """
        global shutdown
        # Пока клиент не остановлен
        while not shutdown:
            try:
                # Получаем данные и адрес отправителя
                data, addr = self.socket.recvfrom(1024)
                data = dict(json.loads(data.decode('utf-8')))
                # Создаем объект сообщения из полученных данных:
                message = Message(**data)
                # Выводим сообщение в консоль:
                sender_name = getattr(message, 'sender_name', str(addr))
                text = getattr(message, 'message', '')
                sys.stdout.write(f'@{sender_name}: {text}\n')
                # Делаем небольшую задержку для уменьшения нагрузки:
                time.sleep(0.2)
            except socket.error as ex:
                # Если возникли проблемы с соединением, завершаем программу.
                print(f"P2PClient.receive: Что-то пошло не так: {ex}")
                shutdown = True
        self.socket.close()

    def send(self):
        """
        Принимает сообщение из потока ввода консоли и посылает его на сервер.
        """
        global shutdown
        # Пока клиент не остановлен
        while not shutdown:
            # Ожидаем ввод данных
            input_data = input()
            if input_data:
                # Создаем объект сообщения из введенных данных:
                message = Message(message=input_data, sender_name=self.name)
                # Отправляем данные:
                data = message.to_json()
                try:
                    self.socket.sendto(data.encode('utf-8'), self.current_connection)
                except socket.error as ex:
                    self.current_connection = None
                    self.send()
            time.sleep(0.2)

    def connect(self):
        """
        "Соединяет" с другим P2P клиентом.
        Сохраняет заданное подключение и посылает клиенту сообщение.
        """
        # Пока клиент не остановлен и соединение не задано
        while not shutdown and not self.current_connection:
            # Вводим, куда подключаться:
            connect_data = input("Connect to (ip:port, like 127.0.0.1:8001):")
            try:
                # Приводим введенные данные к нужному виду (str, int).
                ip, port = connect_data.split(":")
                port = int(port)
                # Отправка сообщения о подключении:
                connect_message = Message(
                    message=f'User @{self.name} wants to chat with you.\n', sender_name=self.name
                )
                data = connect_message.to_json()
                self.current_connection = (ip, port)
                self.socket.sendto(data.encode('utf-8'), self.current_connection)
            except (ValueError, TypeError, AttributeError, socket.error) as ex:
                print(f"Не удается соединиться с {connect_data}, по причине: {ex}.\nПопробуйте снова.")
                self.current_connection = None

    def run(self):
        """
        Запускает работу P2P клиента.
        """
        self.connect()
        # В отдельном потоке вызываем обработку получения сообщений:
        recv_thread = threading.Thread(target=self.receive)
        recv_thread.start()
        # В главном потоке вызываем обработку отправки сообщений:
        self.send()
        # Прикрепляем поток с обработкой получения сообщений к главному потоку:
        recv_thread.join()


if __name__ == '__main__':
    # Задаем настройки распознавания параметров запуска используя argparse:
    parser = argparse.ArgumentParser()
    parser.add_argument("-ho", "--host",
                        help="p2p client host ip address, like 127.0.0.1")
    parser.add_argument("-p", "--port",
                        help="p2p client host port, like 8001")
    args = parser.parse_args()

    try:
        # Устанавливаем параметры P2P клиента
        host = args.host
        port = int(args.port)
        name = input("Name: ").strip()
        # Создаем объект P2P клиента
        p2p_client = P2PClient(host, port, name=name)
        # Запускаем P2P клиента
        p2p_client.run()
    except (TypeError, ValueError):
        print("Incorrect arguments values, use --help/-h for more info.")