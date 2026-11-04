"""Практика 6: потоки, процессы, asyncio + процессы.

Единицы работы импортируются без изменений из variant_4.py.
Запуск: python variant_4_optimized.py --model threads --workers 4
Тесты: python variant_4_optimized.py --test
"""

import argparse
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import math
import multiprocessing as mp
import time
import unittest

from variant_4 import (SCALES, load_document, load_document_async,
                       make_workload, run_sequential, text_features)


def _validate_workers(workers):
    if not isinstance(workers, int) or workers < 1:
        raise ValueError('workers должен быть положительным целым числом')


def _process_document(doc_id):
    """Верхний уровень модуля: функция доступна Windows spawn."""
    return text_features(load_document(doc_id))[2]


def _score_text(text):
    return text_features(text)[2]


def run_threads(doc_ids, workers=4):
    _validate_workers(workers)
    if not doc_ids:
        return 0.0, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # map возвращает результаты в исходном порядке, включая повторы ID.
        total = sum(pool.map(_process_document, doc_ids))
    return total, len(doc_ids)


def run_processes(doc_ids, workers=4):
    _validate_workers(workers)
    if not doc_ids:
        return 0.0, 0
    with ProcessPoolExecutor(max_workers=workers,
                             mp_context=mp.get_context('spawn')) as pool:
        total = sum(pool.map(_process_document, doc_ids, chunksize=4))
    return total, len(doc_ids)


async def run_async(doc_ids, workers=4):
    """Асинхронный интерфейс для уже работающего цикла событий."""
    _validate_workers(workers)
    if not doc_ids:
        return 0.0, 0
    loop = asyncio.get_running_loop()
    semaphore = asyncio.Semaphore(workers * 2)
    with ProcessPoolExecutor(max_workers=workers,
                             mp_context=mp.get_context('spawn')) as pool:
        async def one(doc_id):
            async with semaphore:
                text = await load_document_async(doc_id)
                return await loop.run_in_executor(pool, _score_text, text)

        tasks = [asyncio.create_task(one(doc_id)) for doc_id in doc_ids]
        try:
            scores = await asyncio.gather(*tasks)
        finally:
            # При ошибке отменяем ожидающие задачи и дожидаемся завершения отмены.
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    return sum(scores), len(doc_ids)


def run_asyncio(doc_ids, workers=4):
    """Синхронная обёртка с тем же результатом, что run_sequential."""
    return asyncio.run(run_async(doc_ids, workers))


MODELS = dict(sequential=run_sequential, threads=run_threads,
              processes=run_processes, asyncio=run_asyncio)


def run_task(scale=4, model='threads', workers=4):
    ids = make_workload(scale)  # Генерация ID вне измеряемого интервала.
    start = time.perf_counter()
    fn = MODELS[model]
    score, count = fn(ids) if model == 'sequential' else fn(ids, workers)
    return round(score, 2), count, round(time.perf_counter() - start, 4)


class CorrectnessTests(unittest.TestCase):
    def test_empty(self):
        for fn in MODELS.values():
            self.assertEqual(fn([]), (0.0, 0))

    def test_results_duplicates_and_order(self):
        for ids in ([0], [7, 2, 7, -1, 0], list(range(40))):
            expected = run_sequential(ids)
            for fn in (run_threads, run_processes, run_asyncio):
                actual = fn(ids, workers=2)
                self.assertEqual(actual[1], expected[1])
                self.assertTrue(math.isclose(actual[0], expected[0],
                                             rel_tol=1e-12, abs_tol=1e-9))

    def test_async_loader(self):
        for did in (0, 7, -1):
            self.assertEqual(load_document(did, 0),
                             asyncio.run(load_document_async(did, 0)))

    def test_invalid_workers(self):
        for fn in (run_threads, run_processes, run_asyncio):
            for workers in (0, -1, 1.5):
                with self.assertRaises(ValueError):
                    fn([0], workers)

    def test_exceptions(self):
        # Random не поддерживает list как seed: ошибка должна дойти до вызывающего.
        for fn in (run_threads, run_processes, run_asyncio):
            with self.assertRaises(TypeError):
                fn([[]], workers=2)

    def test_repeated_calls(self):
        expected = run_sequential([3, 1])
        for fn in (run_threads, run_processes, run_asyncio):
            for _ in range(2):
                actual = fn([3, 1], workers=2)
                self.assertTrue(math.isclose(actual[0], expected[0], rel_tol=1e-12))
                self.assertEqual(actual[1], expected[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, default='threads')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    if args.test:
        unittest.main(argv=['variant_4_optimized.py'], verbosity=2)
    else:
        for scale in SCALES:
            print(f'scale={scale}  {run_task(scale, args.model, args.workers)}')


if __name__ == '__main__':
    mp.freeze_support()
    main()
