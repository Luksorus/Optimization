"""
Вариант 4.
"""
import random
import tracemalloc
import time
def load_and_process(n: int) -> tuple[int, float]:
    lines = []
    for i in range(n):
        line = f"{i},{random.random():.6f},{random.randint(0,100)},msg_{i%50}"
        lines.append(line)
    rows = []
    for line in lines:
        parts = line.split(",")
        rows.append({
            "id": int(parts[0]),
            "value": float(parts[1]),
            "code": int(parts[2]),
            "msg": parts[3],
        })
    filtered = [r for r in rows if r["value"] > 0.4]
    s = sum(r["value"] for r in filtered)
    return len(filtered), s

def run_task(n: int):
    return load_and_process(n)

if __name__ == "__main__":
    # Те же размеры, что и в оптимизированной версии — для честного сравнения
    n_values = [50_000, 100_000, 200_000]

    # Заголовок таблицы (идентичен оптимизированной версии)
    print(f"{'N':>8} | {'Результат':<35} | {'Память (МБ)':>12} | {'Время (с)':>10}")
    print("-" * 75)

    for n in n_values:
        # Фиксируем seed для идентичных данных с оптимизированной версией
        random.seed(42)

        # Замер памяти через tracemalloc
        tracemalloc.start()
        start = time.perf_counter()

        res = run_task(n)

        # Получаем пиковое потребление памяти
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed = time.perf_counter() - start

        # Переводим байты в мегабайты
        peak_mb = peak / (1024 * 1024)

        # Вывод в том же формате, что и в оптимизированной версии
        print(f"{n:>8} | {str(res):<35} | {peak_mb:>12.4f} | {elapsed:>10.4f}")
