import time
import random
import numpy as np

def matrix_multiply(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    # Векторизованное умножение матриц с помощью NumPy
    return (np.asarray(a) @ np.asarray(b)).tolist()

def row_stats(matrix: list[list[float]]) -> list[tuple[float, float, float]]:
    arr = np.asarray(matrix)
    # Векторизованное вычисление статистики по строкам (axis=1)
    mins = np.min(arr, axis=1)
    maxs = np.max(arr, axis=1)
    means = np.mean(arr, axis=1)
    
    # Сборка результата в формат, идентичный исходному (список кортежей float)
    return [(float(mn), float(mx), float(mean)) for mn, mx, mean in zip(mins, maxs, means)]

def generate_matrix(n: int) -> list[list[float]]:
    return [[random.random() for _ in range(n)] for _ in range(n)]

def run_task(n: int):
    a = generate_matrix(n)
    b = generate_matrix(n)
    product = matrix_multiply(a, b)
    stats = row_stats(product)
    return round(stats[0][2], 5), round(product[0][0], 5)

if __name__ == "__main__":
    random.seed(42)
    for n in [40,  60, 80]:
        start = time.perf_counter()
        res = run_task(n)
        elapsed = time.perf_counter() - start
        print(f"N={n:3d}  result={res}  time={elapsed:.6f}s")