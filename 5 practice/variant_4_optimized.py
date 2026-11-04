"""Вариант 4: ограниченные LRU/FIFO-кэши с инвалидацией.

python variant_4_optimized.py             # исходный демонстрационный сценарий
python variant_4_optimized.py --test      # автоматические тесты
python variant_4_optimized.py --benchmark # замеры (JSON)
Только стандартная библиотека Python 3.9+; сервисы однопоточные.
"""

import argparse
from collections import OrderedDict
from functools import lru_cache
import gc
import json
import platform
import random
import statistics
import sys
import time
import tracemalloc
import unittest


class OriginalService:
    """Исходная рекурсия без кэша, сохранённая для сравнения."""

    def __init__(self):
        self.modifier = 1.0

    def compute(self, n: int, k: int) -> float:
        if k < 0 or k > n:
            return 0.0
        if k == 0 or k == n:
            return self.modifier
        return self.compute(n - 1, k - 1) + self.compute(n - 1, k) * self.modifier

    def set_modifier(self, value: float) -> None:
        self.modifier = value


class CachedService(OriginalService):
    """Изменение состояния через setter и прямое присваивание очищает кэш."""

    @property
    def modifier(self):
        return self._modifier

    @modifier.setter
    def modifier(self, value):
        self._modifier = value
        self.clear_cache()


class LRUService(CachedService):
    def __init__(self, maxsize: int = 256):
        if not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize должен быть положительным целым числом")
        # Обёртка принадлежит экземпляру: чужие сервисы при очистке не затрагиваются.
        self._cached = lru_cache(maxsize=maxsize)(super().compute)
        super().__init__()

    def compute(self, n: int, k: int) -> float:
        return self._cached(n, k)

    def clear_cache(self):
        self._cached.cache_clear()

    def cache_info(self):
        return self._cached.cache_info()._asdict()


class FIFOService(CachedService):
    """Ручной FIFO: попадание не меняет порядок поступления ключей."""

    def __init__(self, maxsize: int = 256):
        if not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize должен быть положительным целым числом")
        self.maxsize = maxsize
        self._cache = OrderedDict()
        super().__init__()

    def compute(self, n: int, k: int) -> float:
        key = (n, k)
        try:
            value = self._cache[key]
        except KeyError:
            self.misses += 1
            value = super().compute(n, k)
            # Рекурсивные вызовы могли заполнить кэш после первоначальной проверки.
            if len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = value
            return value
        self.hits += 1
        return value

    def clear_cache(self):
        self._cache.clear()
        self.hits = self.misses = 0

    def cache_info(self):
        return dict(hits=self.hits, misses=self.misses,
                    maxsize=self.maxsize, currsize=len(self._cache))


CombinatorialService = LRUService


def make_pairs(max_n=18, queries=80):
    # Локальный генератор сохраняет набор запросов, не меняя глобальный random.
    rng = random.Random(42)
    pairs = [(rng.randint(10, max_n), rng.randint(2, 6)) for _ in range(queries)]
    return pairs + pairs[:queries // 2]


def run_task(max_n: int = 18, queries: int = 80):
    svc = CombinatorialService()
    pairs = make_pairs(max_n, queries)
    t0 = time.perf_counter()
    s = sum(svc.compute(n, k) for n, k in pairs)
    t1 = time.perf_counter()
    svc.set_modifier(1.1)
    s2 = sum(svc.compute(n, k) for n, k in pairs[:20])
    return round(s, 2), round(s2, 2), round(t1 - t0, 4)


class CorrectnessTests(unittest.TestCase):
    def test_equivalence_and_state_changes(self):
        for cls in (LRUService, FIFOService):
            for capacity in (1, 8, 256):
                reference, svc = OriginalService(), cls(capacity)
                for modifier in (1.0, 1.1, 0.0, -0.5, 2.0, 1.0):
                    # Кэш прогрет предыдущей итерацией; проверяется и прямое присваивание.
                    if modifier == -0.5:
                        svc.modifier = modifier
                    else:
                        svc.set_modifier(modifier)
                    reference.set_modifier(modifier)
                    self.assertEqual(svc.cache_info()['currsize'], 0)
                    self.assertEqual(svc.cache_info()['hits'], 0)
                    self.assertEqual(svc.cache_info()['misses'], 0)
                    for n in range(-1, 11):
                        for k in range(-1, max(n, 0) + 2):
                            self.assertEqual(svc.compute(n, k), reference.compute(n, k))
                            self.assertLessEqual(svc.cache_info()['currsize'], capacity)

    def test_repeated_queries(self):
        for cls in (LRUService, FIFOService):
            svc = cls()
            first = svc.compute(18, 6)
            before = svc.cache_info()
            self.assertEqual(svc.compute(18, 6), first)
            self.assertEqual(svc.cache_info()['hits'], before['hits'] + 1)
            self.assertEqual(svc.cache_info()['misses'], before['misses'])

    def test_instance_isolation(self):
        for cls in (LRUService, FIFOService):
            a, b = cls(), cls()
            value = b.compute(10, 3)
            before = b.cache_info()
            a.set_modifier(1.1)
            self.assertEqual(b.cache_info(), before)
            self.assertEqual(b.compute(10, 3), value)

    def test_eviction_policy(self):
        lru, fifo = LRUService(2), FIFOService(2)
        for svc in (lru, fifo):
            for n in (10, 11, 10, 12):
                svc.compute(n, 0)
            before = svc.cache_info()['hits']
            svc.compute(10, 0)
            self.assertEqual(svc.cache_info()['hits'] - before, int(svc is lru))
            self.assertEqual(svc.cache_info()['currsize'], 2)

    def test_original_scenarios(self):
        for max_n in (14, 16, 18):
            ref = OriginalService()
            pairs = make_pairs(max_n, 40)
            first = round(sum(ref.compute(n, k) for n, k in pairs), 2)
            ref.set_modifier(1.1)
            second = round(sum(ref.compute(n, k) for n, k in pairs[:20]), 2)
            self.assertEqual(run_task(max_n, 40)[:2], (first, second))

    def test_capacity_validation(self):
        for cls in (LRUService, FIFOService):
            for capacity in (0, -1, 1.5, None):
                with self.assertRaises(ValueError):
                    cls(capacity)


def execute(svc, pairs, change_each=False):
    total = sum(svc.compute(n, k) for n, k in pairs) if not change_each else 0.0
    if change_each:
        for i, (n, k) in enumerate(pairs):
            svc.set_modifier(1.0 if i % 2 == 0 else 1.1)
            total += svc.compute(n, k)
    else:
        svc.set_modifier(1.1)
        total += sum(svc.compute(n, k) for n, k in pairs[:20])
    return total


def benchmark(repeats=7):
    workloads = [(f'max_n={n}', make_pairs(n, 40), False) for n in (14, 16, 18)]
    # Даже внутренние подзадачи здесь не повторяются: все запросы базовые.
    workloads.append(('unique_base', [(n, 0) for n in range(10, 2010)], False))
    workloads.append(('invalidate_each', [(10, 3)] * 60, True))
    rows = []
    for name, pairs, change_each in workloads:
        expected = execute(OriginalService(), pairs, change_each)
        for cls in (OriginalService, LRUService, FIFOService):
            samples = []
            for _ in range(repeats):
                gc.collect()
                start = time.perf_counter_ns()
                svc = cls()
                result = execute(svc, pairs, change_each)
                samples.append((time.perf_counter_ns() - start) / 1e6)
                assert result == expected, (name, cls.__name__, result, expected)
                del svc
            # Память измеряется отдельно: tracemalloc не искажает замеры времени.
            gc.collect()
            tracemalloc.start()
            svc = cls()
            result = execute(svc, pairs, change_each)
            current, peak = tracemalloc.get_traced_memory()
            info = svc.cache_info() if hasattr(svc, 'cache_info') else None
            tracemalloc.stop()
            assert result == expected
            rows.append(dict(workload=name, strategy=cls.__name__,
                             median_ms=statistics.median(samples),
                             min_ms=min(samples), max_ms=max(samples),
                             retained_bytes=current, peak_bytes=peak,
                             result=result, cache_after_last_invalidation=info))
            del svc
    return dict(python=sys.version, platform=platform.platform(),
                processor=platform.processor(), repeats=repeats, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    if args.test:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    elif args.benchmark:
        print(json.dumps(benchmark(), ensure_ascii=False, indent=2))
    else:
        for mn in (14, 16, 18):
            print(f'max_n={mn}  {run_task(max_n=mn, queries=40)}')


if __name__ == '__main__':
    main()
