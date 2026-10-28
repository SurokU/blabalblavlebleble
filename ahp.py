# Лабораторная работа - Метод анализа иерархий (МАИ) Т. Саати, один уровень.
# Программа помогает расставить приоритеты между критериями: пользователь
# сравнивает критерии попарно, а программа превращает эти суждения в
# весовые коэффициенты и проверяет, не противоречат ли суждения друг другу.

import re
import sys

# Без явной UTF-8 консоль Windows (особенно Git Bash) искажает русский
# текст и символ λ, поэтому настраиваем кодировку до любого вывода
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stdin.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

MIN_N, MAX_N = 2, 10
# Индексы случайной согласованности Саати: с ними сравнивается
# согласованность матрицы пользователя, чтобы понять, лучше ли его
# оценки случайных. Значение для n = 1 и 2 равно нулю - матрица 2x2
# согласована всегда
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
                7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
# Порог Саати: при большем отношении согласованности оценки считаются
# противоречивыми и веса по ним доверия не заслуживают
CR_LIMIT = 0.10


class Interrupted(Exception):
    # Отдельное исключение позволяет из любого места диалога корректно
    # выйти в main(), не дублируя обработку Ctrl+C в каждой функции
    pass


def ask(prompt):
    # Единая точка ввода: превращает Ctrl+C и конец потока в Interrupted,
    # чтобы пользователь не видел аварийного сообщения Python
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        raise Interrupted


def print_scale():
    # Без подсказки пользователь не знает, что значат числа 1-9,
    # и вводит оценки наугад - отсюда несогласованные матрицы
    print("Шкала Саати (насколько первый критерий важнее второго):")
    print("  1 - одинаково важны          3 - немного важнее")
    print("  5 - заметно важнее           7 - значительно важнее")
    print("  9 - абсолютно важнее         2, 4, 6, 8 - промежуточные оценки")
    print("Если важнее второй критерий, введите обратную дробь: 1/3, 1/5 ...")
    print("Можно вводить целые (3), дроби (1/3) и десятичные числа (0,5).")


def parse_count(text):
    # Проверка вынесена отдельно от диалога, чтобы сообщение об ошибке
    # точно объясняло, что не так, а не просто «неверный ввод»
    raw = text.strip()
    if raw == "":
        return None, "ничего не введено"
    if re.fullmatch(r"[+-]?\d+[.,]\d*", raw):
        return None, "количество критериев - целое число"
    if not re.fullmatch(r"[+-]?\d+", raw):
        return None, "«" + raw + "» не является числом"
    n = int(raw)
    if n < MIN_N:
        return None, ("критериев должно быть не меньше " + str(MIN_N) +
                      " - сравнивать один критерий не с чем")
    if n > MAX_N:
        return None, ("критериев должно быть не больше " + str(MAX_N) +
                      " - при большем числе попарные оценки становятся "
                      "ненадёжными")
    return n, None


def ask_count():
    # Повторяем вопрос до корректного ответа, чтобы ошибка ввода
    # не завершала программу и не сбрасывала уже сделанное
    while True:
        n, error = parse_count(ask("Введите количество критериев (от " +
                                   str(MIN_N) + " до " + str(MAX_N) +
                                   ", например 3): "))
        if error is None:
            return n
        print("  Ошибка: " + error + ". Повторите ввод.")


def ask_names(n):
    # Осмысленные названия делают вопросы понятнее («Цена» или «Кр 1»?),
    # но вводить их необязательно - Enter оставляет номер критерия
    print("Введите названия критериев или нажмите Enter, чтобы оставить "
          "номер.")
    names = []
    for i in range(1, n + 1):
        while True:
            name = ask("  Критерий " + str(i) + ": ").strip()
            if name == "":
                name = "Кр " + str(i)
            if len(name) > 20:
                print("  Ошибка: название длиннее 20 символов, оно не "
                      "поместится в таблицу. Сократите его.")
            elif name in names:
                print("  Ошибка: критерий «" + name + "» уже есть. "
                      "Названия должны различаться.")
            else:
                names.append(name)
                break
    return names


def parse_rating(text):
    # Оценку можно ввести тремя привычными способами (3, 1/3, 0,5);
    # всё остальное отклоняется с объяснением, чтобы в матрицу не попало
    # значение вне шкалы Саати
    raw = text.strip().replace(" ", "").replace(",", ".")
    if raw == "":
        return None, "оценка не введена"
    if raw.startswith("-"):
        return None, "оценка должна быть положительной"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", raw)
    if m:
        if float(m.group(2)) == 0:
            return None, "деление на ноль"
        value = float(m.group(1)) / float(m.group(2))
    elif re.fullmatch(r"\d+(?:\.\d+)?", raw):
        value = float(raw)
    else:
        return None, ("«" + text.strip() + "» не является оценкой. "
                      "Введите число от 1 до 9 или дробь вида 1/3")
    # Небольшой допуск, чтобы 0.111 считалось равным 1/9
    if value <= 0:
        return None, "оценка должна быть больше нуля"
    if value > 9 + 1e-9:
        return None, "оценка не может быть больше 9 - это предел шкалы Саати"
    if value < 1 / 9 - 1e-3:
        return None, ("оценка не может быть меньше 1/9 - это предел шкалы "
                      "Саати")
    return value, None


def ask_rating(first, second):
    # Вопрос формулируется через названия критериев, чтобы пользователь
    # не путал, какой из двух считается «первым»
    while True:
        text = ask("Насколько «" + first + "» важнее, чем «" + second +
                   "»? ")
        value, error = parse_rating(text)
        if error is None:
            return value
        print("  Ошибка: " + error + ". Повторите ввод.")


def fill_matrix(names):
    # Спрашиваем только пары выше диагонали: остальное следует из
    # свойств матрицы (a_ii = 1, a_ji = 1 / a_ij), и лишние вопросы
    # лишь дали бы пользователю шанс ввести противоречивые данные
    n = len(names)
    matrix = [[1.0] * n for _ in range(n)]
    total = n * (n - 1) // 2
    number = 0
    for i in range(n):
        for j in range(i + 1, n):
            number += 1
            print("Сравнение " + str(number) + " из " + str(total) + ".")
            value = ask_rating(names[i], names[j])
            matrix[i][j] = value
            matrix[j][i] = 1 / value
    return matrix


def geometric_weights(matrix):
    # Среднее геометрическое строки - стандартное приближение собственного
    # вектора матрицы в МАИ: оно устойчиво к небольшим несогласованностям
    # и, в отличие от суммы строки, не зависит от масштаба оценок
    n = len(matrix)
    means = []
    for row in matrix:
        product = 1.0
        for value in row:
            product *= value
        means.append(product ** (1 / n))
    total = sum(means)
    return means, [m / total for m in means]


def consistency(matrix, weights):
    # Веса имеют смысл, только если суждения не противоречат друг другу
    # (если A важнее B, а B важнее C, то A должно быть важнее C).
    # Мерой служит отношение согласованности ОС = ИС / СИ
    n = len(matrix)
    lambda_max = sum(sum(matrix[i][j] * weights[j] for j in range(n)) /
                     weights[i] for i in range(n)) / n
    ci = (lambda_max - n) / (n - 1)
    ri = RANDOM_INDEX[n]
    cr = ci / ri if ri > 0 else 0.0
    return lambda_max, ci, cr


def format_rating(value):
    # Оценки показываются так, как их привычно записывать по шкале
    # Саати (3, 1/3), а не как 0.3333333 - так таблицу легче сверить
    # с тем, что вводилось
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    inverse = 1 / value
    if abs(inverse - round(inverse)) < 1e-9:
        return "1/" + str(int(round(inverse)))
    return format(value, ".2f")


def print_matrix(names, matrix, means, weights):
    # Полная таблица позволяет проверить, что программа правильно поняла
    # ввод, и показывает, из чего получены веса
    width = max(8, max(len(s) for s in names) + 1)
    head = " " * width + "".join(s.rjust(width) for s in names)
    print(head + "   Ср. геом.   Вес")
    for name, row, mean, weight in zip(names, matrix, means, weights):
        cells = "".join(format_rating(v).rjust(width) for v in row)
        print(name.ljust(width) + cells + format(mean, ".3f").rjust(12) +
              format(weight, ".2f").rjust(6))


def print_result(names, weights):
    # Итог выводится отдельно и по убыванию веса: пользователю важнее
    # всего порядок критериев, а не промежуточные вычисления
    print("Весовые коэффициенты критериев (по убыванию):")
    order = sorted(range(len(names)), key=lambda i: -weights[i])
    for place, i in enumerate(order, 1):
        print("  " + str(place) + ". " + names[i].ljust(20) +
              format(weights[i], ".2f"))
    rounded = sum(round(w, 2) for w in weights)
    if abs(rounded - 1) > 1e-9:
        # Без пояснения сумма 0.99 или 1.01 выглядит как ошибка расчёта
        print("  Сумма округлённых весов " + format(rounded, ".2f") +
              " вместо 1.00 - это погрешность округления до сотых.")


def ask_choice(prompt):
    # Вопросы «да/нет» принимают только 1 или 0: цифры одинаковы
    # в любой раскладке, а случайный ответ не приведёт к выходу
    while True:
        answer = ask(prompt + " Введите 1 - да, 0 - нет: ").strip().lower()
        if answer in ("1", "д", "да"):
            return True
        if answer in ("0", "н", "нет"):
            return False
        print("  Ошибка: введите 1 или 0.")


def run_once():
    # Один полный расчёт; вынесен из main(), чтобы его можно было
    # повторить без перезапуска программы
    n = ask_count()
    names = ask_names(n)
    print()
    print_scale()
    while True:
        print()
        matrix = fill_matrix(names)
        means, weights = geometric_weights(matrix)
        lambda_max, ci, cr = consistency(matrix, weights)
        print()
        print_matrix(names, matrix, means, weights)
        print()
        if n > 2:
            print("Проверка согласованности: λmax = " +
                  format(lambda_max, ".3f") + ", ИС = " + format(ci, ".3f") +
                  ", ОС = " + format(cr, ".3f") + " (допустимо до " +
                  format(CR_LIMIT, ".2f") + ").")
        if cr <= CR_LIMIT:
            if n > 2:
                print("Оценки согласованы, весам можно доверять.")
            print()
            print_result(names, weights)
            return
        # При несогласованных оценках веса формально считаются, но
        # опираться на них нельзя - поэтому предлагаем исправить ввод
        print("Внимание: оценки противоречат друг другу (ОС > " +
              format(CR_LIMIT, ".2f") + ").")
        print("Проверьте, что если A важнее B, а B важнее C, то и A "
              "важнее C.")
        if not ask_choice("Ввести сравнения заново?"):
            print()
            print_result(names, weights)
            print("  Учтите: веса получены по несогласованным оценкам.")
            return


def main():
    print("Метод анализа иерархий Т. Саати")
    print("Программа рассчитывает весовые коэффициенты критериев по их")
    print("попарному сравнению и проверяет согласованность оценок.")
    try:
        while True:
            print()
            run_once()
            print()
            if not ask_choice("Выполнить новый расчёт?"):
                print("Работа программы завершена.")
                break
    except Interrupted:
        print()
        print("Работа программы прервана пользователем.")


if __name__ == "__main__":
    main()
