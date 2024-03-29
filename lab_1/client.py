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
        if 'join' not in data:
            self.join = False

        # Распаковываем кортеж именованных аргументов в параметры класса.
        # Паттерн Builder
        for param, value in data.items():
            setattr(self, param, value)

        # время получения сообщения:
        self.curr_time = time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime())

    def to_json(self):
        """
            Возвращает атрибуты класса и их значения в виде json.
            Использует стандартный модуль python - json.
        """
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class ClientHandler:
    """
        Класс-Обработчик с бизнес-логикой клиента.
        Реализует методы получения и отображения сообщений
    """

    def __init__(self, server_addr=('localhost', 8888), client_addr=('localhost', 0)):
        global shutdown
        # Флаг сигнализирующий об успешном подключении
        join = False
        # Пытаемся создать соединение, если его еще нет или клиент не остановлен
        while not shutdown and not join:
            try:
                # Имя клиента в чате:
                self.name = input("Name: ").strip()
                # Адрес сервера (ip, port) к которому происходит подключение:
                self.server_addr = server_addr
                # Создание сокета:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Подключение сокета:
                self.socket.connect(client_addr)
                join = True
                # Отправка сообщения о подключении:
                connect_message = Message(
                  join=join,
                  message=f'User @{self.name} has joint to chat\n',
                  sender_name=self.name
                )
                connect_message_data = connect_message.to_json()
                self.socket.sendto(connect_message_data.encode('utf-8'), self.server_addr)
            except Exception as ex:
                print(f"ClientHandler.__init__: Что-то пошло не так: {ex}")
                shutdown = True

    @staticmethod
    def show_message(message_obj: Message):
        """
            Выводит полученное сообщение в стандартный поток вывода (консоль)
        """
        if message_obj.join:
            # Если сообщение о подключении, то выводим только его:
            sys.stdout.write(message_obj.message)
        else:
            # Иначе, добавляем имя отправителя в вывод:
            sys.stdout.write(f'@{message_obj.sender_name}: {message_obj.message}\n')

    def receive(self):
        """
            Получает сообщение из сокета и передает его в обработчик
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
                # Вызываем обработчик показа сообщения:
                self.show_message(message)
                time.sleep(0.2)
            except Exception as ex:
                print(f"ClientHandler.receive: Что-то пошло не так: {ex}")
                shutdown = True

    def send(self):
        """
            Принимает сообщение из потока ввода консоли,
            отправляет его в обработчик и посылает на сервер.
        """
        global shutdown
        # Пока клиент не остановлен
        while not shutdown:
            try:
                # Ожидаем ввод данных
                input_data = input("").strip()
                if input_data:
                    # Создаем объект сообщения из введенных данных:
                    message = Message(message=input_data, sender_name=self.name)
                    # Отправляем данные на сервер:
                    data = message.to_json()
                    self.socket.sendto(data.encode('utf-8'), self.server_addr)
                time.sleep(0.2)
            except Exception as ex:
                print(f"ClientHandler.send: Что-то пошло не так: {ex}")
                shutdown = True


if __name__ == '__main__':
    # Создаем обработчик клиента
    handler = ClientHandler(server_addr=('localhost', 8888), client_addr=('localhost', 0))
    # В отдельном потоке вызываем обработку получения сообщений:
    recv_thread = threading.Thread(target=handler.receive)
    recv_thread.start()
    # В главном потоке вызываем обработку отправки сообщений:
    handler.send()
    # Прикрепляем поток с обработкой получения сообщений к главному потоку:
    recv_thread.join()
