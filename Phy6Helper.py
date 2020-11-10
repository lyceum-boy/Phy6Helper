#!/usr/bin/python3
# -*- coding: utf-8 -*-

import math
import sys

import csv
import datetime
import pyperclip
import sqlite3

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QWidget

widgets = list()


class Phy6HelperException(Exception):
    pass


class CaseIsEmptyError(Phy6HelperException):
    pass


class NoElementIsChosenError(Phy6HelperException):
    pass


class NoElementsInListError(Phy6HelperException):
    pass


class PastDayAdditionError(Phy6HelperException):
    pass


class TableViewerWidget(QWidget):

    def __init__(self, image_name, window_title):
        super().__init__()
        self.image_name = image_name
        self.window_title = window_title
        self.pixmap = self.image = None
        self.initUI()

    # noinspection PyPep8Naming
    def initUI(self):
        try:
            image = open(f'{self.image_name}')
            image.close()
        except FileNotFoundError:
            QMessageBox.critical(self, "Ошибка!",
                                 f'Файл "{self.image_name}" '
                                 f'отсутствует в директории приложения.',
                                 QMessageBox.Ok)
            self.close()
        else:
            self.pixmap = QPixmap(f'{self.image_name}')
            # Если картинки нет, то QPixmap будет пустым,
            # а исключения не будет
            width, height = self.pixmap.width(), self.pixmap.height()
            self.resize(width, height)
            self.setWindowTitle(self.window_title)
            self.setWindowIcon(QIcon('WindowIcon.ico'))
            self.image = QLabel(self)
            self.image.move(0, 0)
            self.image.resize(width, height)
            # Отображаем содержимое QPixmap в объекте QLabel
            self.image.setPixmap(self.pixmap)


class Phy6Helper(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Phy6 Helper')
        self.setWindowIcon(QIcon('WindowIcon.ico'))

        uic.loadUi('design.ui', self)

        self.connection = sqlite3.connect("db.s3db")
        self.cursor = self.connection.cursor()

        request = "SELECT button FROM connection"
        self.button_names = list()
        for line in self.cursor.execute(request).fetchall():
            self.button_names.append(line[0].replace('\\n', '\n'))

        request = "SELECT size FROM connection"
        self.font_sizes = list()
        for line in self.cursor.execute(request).fetchall():
            self.font_sizes.append(line[0])
        self.font_sizes = iter(self.font_sizes)

        request = "SELECT image FROM connection"
        self.connection_info = dict()
        for button, image in zip(self.button_names,
                                 self.cursor.execute(request).fetchall()):
            self.connection_info[button] = image[0]

        numbers = [i for i in range(10)]
        codes = [i for i in range(48, 58)]
        self.key_connections = dict()
        for number, code in zip(numbers, codes):
            self.key_connections[code] = number

        self.pushButton_table_n = None
        self.current_file = self.window_title = None

        self.first_number = 0.0
        self.second_number = 0.0
        self.values_amount = 0.0
        self.values_result = 0.0
        self.current_operator = ""
        self.second_input_flag = False
        self.btn0.clicked.connect(self.number_function)

        numbers = [self.btn0, self.btn1, self.btn2, self.btn3, self.btn4,
                   self.btn5, self.btn6, self.btn7, self.btn8, self.btn9]
        operators = [self.btn_plus, self.btn_minus, self.btn_mult,
                     self.btn_div, self.btn_pow]

        for number in numbers:
            number.clicked.connect(self.number_function)
        for operator in operators:
            operator.clicked.connect(self.operator_function)

        self.btn_clear.clicked.connect(self.clear_function)
        self.btn_eq.clicked.connect(self.equal_function)

        self.btn_dot.clicked.connect(self.dot_function)
        self.btn_pi.clicked.connect(self.pi_function)
        self.btn_op.clicked.connect(self.op_function)
        self.btn_sqrt.clicked.connect(self.sqrt_function)
        self.btn_fact.clicked.connect(self.fact_function)

        self.btn_sin.clicked.connect(self.sin_function)
        self.btn_cos.clicked.connect(self.cos_function)
        self.btn_tan.clicked.connect(self.tan_function)

        self.initUI()

    # noinspection PyPep8Naming
    def initUI(self):
        """"""

        # Воспользуемся циклом для оптимального создания кнопок
        positions = [(j, i) for i in range(6) for j in range(3)]
        names = self.button_names
        for position, name in zip(positions, names):
            self.pushButton_table_n = QPushButton(self.tab_4)
            x, y = position
            x, y = x * (240 + 10), y * (80 + 10)
            self.pushButton_table_n.setGeometry(x + 10, y + 10, 240, 80)
            font = QFont()
            font.setFamily("Segoe UI")
            font.setPointSize(next(self.font_sizes))
            self.pushButton_table_n.setFont(font)
            self.pushButton_table_n.setText(name)
            self.pushButton_table_n.clicked.connect(self.open_widget)

        try:
            csvfile = open('cases.csv', mode='r', encoding='utf8')
            csvfile.close()
        except FileNotFoundError:
            csvfile = open('cases.csv', mode='w', encoding='utf-8', newline='')
            csvfile.close()
        finally:
            with open('cases.csv', mode='r', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                for row in reader:
                    self.listWidget_cases.addItem(
                        f'{row[0]}    {row[1]}    —    {row[2]}')

            today = datetime.datetime.today()
            time = QTime(today.hour, today.minute)
            self.timeEdit.setTime(time)
            self.pushButton_add_case.clicked.connect(self.add_case)
            self.pushButton_delete_case.clicked.connect(self.delete_case)

    # ====================== CALCULATOR METHODS ======================

    def number_function(self):
        sender = self.sender()
        self.second_number = int(sender.text())
        str_sn = str(self.second_number)
        if not self.second_input_flag:
            if self.table.value() == 0.0:
                self.table.display(str_sn)
            else:
                self.table.display(
                    self.destroy_zero(self.table.value()) + str_sn)
        else:
            self.table.display(str_sn)
            self.second_input_flag = False

    def operator_function(self):
        self.values_amount += 1
        if self.values_amount > 1:
            self.equal_function()
        self.first_number = self.destroy_zero(self.table.value())
        sender = self.sender()
        self.current_operator = sender.text()
        self.second_input_flag = True

    def clear_function(self):
        self.table.display(0)
        self.first_number = 0.0
        self.second_number = 0.0
        self.values_amount = 0.0
        self.values_result = 0.0
        self.current_operator = ""
        self.second_input_flag = False

    def equal_function(self):
        # noinspection PyBroadException
        try:
            self.values_amount = 0
            self.second_number = self.destroy_zero(self.table.value())
            if self.current_operator == "+":
                self.values_result = float(self.first_number) + \
                                     float(self.second_number)
            elif self.current_operator == "-":
                self.values_result = float(self.first_number) - \
                                     float(self.second_number)
            elif self.current_operator == "*":
                self.values_result = float(self.first_number) * \
                                     float(self.second_number)
            elif self.current_operator == "/":
                self.values_result = float(self.first_number) / \
                                     float(self.second_number)
            elif self.current_operator == "^":
                self.values_result = float(self.first_number) ** \
                                     float(self.second_number)
            self.table.display(self.destroy_zero(self.values_result))
            self.second_input_flag = True
        except OverflowError:
            QMessageBox.critical(self, "Ошибка!", "Слишком большой результат.",
                                 QMessageBox.Ok)
        except ZeroDivisionError:
            QMessageBox.critical(self, "Ошибка!",
                                 "Ошибка при выполнении деления на ноль.",
                                 QMessageBox.Ok)
        except Exception:
            QMessageBox.critical(self, "Ошибка!",
                                 "Пожалуйста, проверьте корректность ввода.",
                                 QMessageBox.Ok)

    def dot_function(self):
        if "." not in self.destroy_zero(self.table.value()):
            self.table.display(self.destroy_zero(self.table.value()) + ".")

    def pi_function(self):
        self.first_number = float(self.table.value())
        self.first_number = math.pi
        print(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    def op_function(self):
        self.first_number = float(self.table.value())
        self.first_number = -self.first_number
        print(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    def sqrt_function(self):
        self.first_number = float(self.table.value())
        self.first_number = self.first_number ** 0.5
        print(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    def fact_function(self):
        self.first_number = float(self.table.value())
        self.first_number = math.factorial(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    def sin_function(self):
        self.first_number = float(self.table.value())
        self.first_number = math.sin(self.first_number)
        print(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    def cos_function(self):
        self.first_number = float(self.table.value())
        self.first_number = math.cos(self.first_number)
        print(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    def tan_function(self):
        self.first_number = float(self.table.value())
        self.first_number = math.tan(self.first_number)
        print(self.first_number)
        self.table.display(self.destroy_zero(self.first_number))

    @staticmethod
    def destroy_zero(num: float):
        return str(num)[:-2] if str(num).endswith('.0') else str(num)

    # ===================== TABLE VIEWER METHODS =====================

    def open_widget(self):
        global widgets
        self.current_file = self.connection_info[self.sender().text()]
        self.window_title = self.sender().text().replace('\n', ' ')
        widget = TableViewerWidget(self.current_file, self.window_title)
        widgets.append(widget)
        widget.setFixedSize(widget.width(), widget.height())
        widget.show()

    # ===================== TASK PLANNER METHODS =====================

    def add_case(self):
        year, month, day, hour, minute, case = self.receive_case_info()
        try:
            if not case:
                raise CaseIsEmptyError("self.lineEdit.text() -> ''")
            if self.check_wrong_case_addition():
                res = f'{day}.{month}.{year}    {hour}:{minute}    —    {case}'
                self.listWidget_cases.addItem(res)
                self.listWidget_cases.sortItems()
                self.lineEdit_case.clear()
            else:
                raise PastDayAdditionError
        except CaseIsEmptyError:
            QMessageBox.critical(self, "Ошибка!",
                                 "Введите описание события.",
                                 QMessageBox.Ok)
        except PastDayAdditionError:
            QMessageBox.critical(self, "Ошибка!",
                                 "Вы не можете добавить событие на уже "
                                 "прошедшее время.",
                                 QMessageBox.Ok)
            print(self.receive_current_dt())
            print(self.receive_case_info())

    def delete_case(self):
        try:
            if not self.listWidget_cases.count():
                raise NoElementsInListError('self.listWidget.count() -> 0')
            if self.listWidget_cases.currentItem():
                row = self.listWidget_cases.currentRow()
                self.listWidget_cases.takeItem(row)
            else:
                raise NoElementIsChosenError(
                    'listWidget.currentItem() -> None')
        except NoElementsInListError:
            QMessageBox.critical(self, "Ошибка!",
                                 "Вы не добавили ни одно событие.",
                                 QMessageBox.Ok)
        except NoElementIsChosenError:
            QMessageBox.critical(self, "Ошибка!",
                                 "Выделите событие, которое хотите удалить.",
                                 QMessageBox.Ok)
        finally:
            self.listWidget_cases.sortItems()

    def receive_case_info(self):
        day = self.calendar.selectedDate().day()
        month = self.calendar.selectedDate().month()
        year = self.calendar.selectedDate().year()
        hour = self.timeEdit.time().hour()
        minute = self.timeEdit.time().minute()
        case = self.lineEdit_case.text()
        day = str(day).rjust(2, '0')
        month = str(month).rjust(2, '0')
        year = str(year).rjust(2, '0')
        hour = str(hour).rjust(2, '0')
        minute = str(minute).rjust(2, '0')
        return year, month, day, hour, minute, case

    @staticmethod
    def receive_current_dt():
        today = datetime.datetime.today()
        return today.year, today.month, today.day, today.hour, today.minute

    def check_wrong_case_addition(self):
        year, month, day, hour, minute = [int(x) for x in
                                          self.receive_case_info()[:-1]]
        year_c, month_c, day_c, hour_c, minute_c = self.receive_current_dt()
        input_date = datetime.datetime(year=year, month=month, day=day,
                                       hour=hour, minute=minute)
        current_date = datetime.datetime(year=year_c, month=month_c, day=day_c,
                                         hour=hour_c, minute=minute_c)
        return input_date >= current_date

    # ===============================================================

    def closeEvent(self, event):
        # При закрытии формы закроем и наше соединение
        # с базой данных
        self.connection.close()

        items = list()
        for row in range(self.listWidget_cases.count()):
            items.append(self.listWidget_cases.item(row).text())
        for i in range(len(items)):
            items[i] = [*items[i].split('    —    ')[0].split('    '),
                        items[i].split('    —    ')[1]]
        with open('cases.csv', mode='w', encoding='utf-8',
                  newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
            writer.writerows(items)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            reply = QMessageBox.warning(self, "Подвердите выход!",
                                        "Вы действительно хотите выйти?",
                                        QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.closeEvent(QCloseEvent)
                quit()

        if self.tabWidget.currentIndex() == 2:
            if event.key() in self.key_connections.keys():
                exec(f'self.btn{self.key_connections[event.key()]}.click()')
            elif int(event.modifiers()) == Qt.ControlModifier:
                if event.key() == Qt.Key_V:
                    pyperclip.copy('3.1415')
                    try:
                        float(pyperclip.paste())
                    except ValueError:
                        pass
                    else:
                        self.table.display(
                            self.destroy_zero(float(pyperclip.paste())))
        elif self.tabWidget.currentIndex() == 5:
            if event.key() == Qt.Key_Return:
                self.add_case()
            elif event.key() == Qt.Key_Delete or \
                    event.key() == Qt.Key_Backspace:
                self.delete_case()


def main():
    app = QApplication(sys.argv)
    exe = Phy6Helper()
    exe.setFixedSize(exe.width(), exe.height())
    exe.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
