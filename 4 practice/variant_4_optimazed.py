import random
import time
import tracemalloc
def load_and_process(n: int) -> tuple[int, float]:
    filtered_count = 0
    total_sum = 0.0
    for i in range(n):
        val = float(f"{random.random():.6f}")
        _ = random.randint(0, 100)
        if val > 0.4:
            filtered_count += 1
            total_sum += val
    return filtered_count, total_sum
def run_task(n: int) -> tuple[int, float]:
    return load_and_process(n)
if __name__ == "__main__":
    random.seed(42)
    n_values = [50_000, 100_000, 200_000]
    print(f"{'N':>8} | {'Результат':<35} | {'Память (МБ)':>12} | {'Время (с)':>10}")
    print("-" * 75)
    for n in n_values:
        random.seed(42)  
        tracemalloc.start()
        start = time.perf_counter()
        res = run_task(n)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed = time.perf_counter() - start
        peak_mb = peak / (1024 * 1024)
        print(f"{n:>8} | {str(res):<35} | {peak_mb:>12.4f} | {elapsed:>10.4f}")