# Лабораторная работа - Метод анализа иерархий (МАИ) Т. Саати, один уровень.
# Программа помогает расставить приоритеты между критериями: пользователь
# сравнивает критерии попарно, а программа превращает эти суждения в
# весовые коэффициенты.

from fractions import Fraction


def fill_matrix(n):
    # Спрашиваем только пары выше диагонали: остальное следует из
    # свойств матрицы (a_ii = 1, a_ji = 1 / a_ij)
    matrix = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            # Fraction позволяет вводить оценку и как 3, и как 1/3
            value = float(Fraction(input("Насколько Кр " + str(i + 1) +
                                         " важнее, чем Кр " + str(j + 1) +
                                         "? ")))
            matrix[i][j] = value
            matrix[j][i] = 1 / value
    return matrix


def geometric_weights(matrix):
    # Среднее геометрическое строки - стандартное приближение собственного
    # вектора матрицы в МАИ
    n = len(matrix)
    means = []
    for row in matrix:
        product = 1.0
        for value in row:
            product *= value
        means.append(product ** (1 / n))
    total = sum(means)
    return [m / total for m in means]


def main():
    print("Метод анализа иерархий Т. Саати")
    n = int(input("Введите количество критериев: "))
    matrix = fill_matrix(n)
    weights = geometric_weights(matrix)
    print("Весовые коэффициенты критериев:")
    for i, w in enumerate(weights, 1):
        print("  Кр " + str(i) + ": " + format(w, ".2f"))


if __name__ == "__main__":
    main()
