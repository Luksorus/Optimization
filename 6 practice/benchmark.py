"""Воспроизводимые эксперименты: --stage analyze, --stage benchmark.

Каждый вариант: один непротоколируемый прогрев, затем 5 измерений.
Запускать обычным Python из терминала, без профилировщика.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import pickle
import platform
import statistics
import sys
import time

from variant_4 import _make_text, text_features, run_sequential
from variant_4_optimized import MODELS, _score_text

ROOT = Path(__file__).resolve().parent
SIZES = (1, 40, 160, 320, 1280)
REPEATS = 5


def stats(values):
    return dict(median_s=statistics.median(values), min_s=min(values), max_s=max(values))


def environment():
    return dict(python=sys.version, platform=platform.platform(),
                processor=platform.processor(), logical_cpus=os.cpu_count(),
                repeats=REPEATS, start_method='spawn',
                cold_pool_each_call=True, sizes=SIZES)


def write(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def analyze():
    data = dict(environment=environment(), rows=[])
    for n in SIZES:
        ids = list(range(n))
        observations = []
        for repeat in range(REPEATS + 1):
            waits = generation = cpu = 0.0
            scores = []
            for did in ids:
                t = time.perf_counter()
                time.sleep(0.005)
                waits += time.perf_counter() - t
                t = time.perf_counter()
                text = _make_text(did)
                generation += time.perf_counter() - t
                t = time.perf_counter()
                scores.append(text_features(text)[2])
                cpu += time.perf_counter() - t
            t = time.perf_counter()
            total = 0.0
            for score in scores:
                total += score
            reduction = time.perf_counter() - t
            if repeat:
                observations.append(dict(wait_s=waits, generation_s=generation,
                                         features_s=cpu, reduction_s=reduction))
        row = dict(n=n, components={key: stats([r[key] for r in observations])
                                    for key in observations[0]})
        med = {key: value['median_s'] for key, value in row['components'].items()}
        denominator = sum(med.values())
        row['shares'] = {key: value / denominator for key, value in med.items()}
        f_threads = 1.0 - row['shares']['wait_s']
        f_process = row['shares']['reduction_s']
        row['amdahl_threads'] = {str(p): 1 / (f_threads + (1-f_threads)/p)
                                 for p in (2, 4, 8)}
        row['amdahl_processes_optimistic'] = {
            str(p): 1 / (f_process + (1-f_process)/p) for p in (2, 4, 8)}
        data['rows'].append(row)
        write('analysis_results.json', data)
        print(f'analysis n={n}: wait={row["shares"]["wait_s"]:.1%}, '
              f'CPU={f_threads:.1%}', flush=True)
    texts = [_make_text(did) for did in range(40)]
    data['payload'] = dict(mean_text_chars=statistics.mean(map(len, texts)),
                           mean_pickle_text_bytes=statistics.mean(
                               len(pickle.dumps(text)) for text in texts),
                           pickle_id_bytes=len(pickle.dumps(10)),
                           pickle_score_bytes=len(pickle.dumps(1.0)))
    write('analysis_results.json', data)


def _wait(seconds):
    time.sleep(seconds)
    return 1.0


def diagnostic(kind, model, values, workers):
    fn = _score_text if kind == 'cpu_only' else _wait
    if model == 'sequential':
        return sum(map(fn, values)), len(values)
    cls = ThreadPoolExecutor if model == 'threads' else ProcessPoolExecutor
    kwargs = dict(max_workers=workers)
    if model == 'processes':
        kwargs['mp_context'] = mp.get_context('spawn')
    with cls(**kwargs) as pool:
        total = sum(pool.map(fn, values, chunksize=4))
    return total, len(values)


def timed(fn, expected):
    samples = []
    # Прогрев тоже создаёт и закрывает пул; последующие вызовы остаются холодными.
    for repeat in range(REPEATS + 1):
        start = time.perf_counter()
        actual = fn()
        elapsed = time.perf_counter() - start
        assert actual[1] == expected[1]
        assert math.isclose(actual[0], expected[0], rel_tol=1e-12, abs_tol=1e-8)
        if repeat:
            samples.append(elapsed)
    return dict(**stats(samples), result=actual, samples_s=samples)


def benchmark():
    if not (ROOT / 'analysis_results.json').exists():
        raise SystemExit('Сначала выполните --stage analyze и зафиксируйте прогноз.')
    data = dict(environment=environment(), rows=[], sweep=[], diagnostics=[])
    for n in SIZES:
        ids = list(range(n))
        expected = None
        for name, fn in MODELS.items():
            if expected is None:
                expected = run_sequential(ids)
            call = (lambda: fn(ids)) if name == 'sequential' else (lambda: fn(ids, workers=4))
            row = dict(n=n, model=name, workers=1 if name == 'sequential' else 4,
                       **timed(call, expected))
            data['rows'].append(row)
            write('benchmark_results.json', data)
            print(f'{name:10} n={n:4}: {row["median_s"]:.4f}s', flush=True)
    ids = list(range(320))
    expected = run_sequential(ids)
    for workers in (2, 8):
        for name in ('threads', 'processes', 'asyncio'):
            fn = MODELS[name]
            row = dict(n=len(ids), model=name, workers=workers,
                       **timed(lambda: fn(ids, workers=workers), expected))
            data['sweep'].append(row)
            write('benchmark_results.json', data)
            print(f'sweep {name} p={workers}: {row["median_s"]:.4f}s', flush=True)
    texts = [_make_text(did) for did in range(160)]
    for kind, values in (('cpu_only', texts), ('io_only', [0.005] * 160)):
        expected = diagnostic(kind, 'sequential', values, 1)
        for name in ('sequential', 'threads', 'processes'):
            workers = 1 if name == 'sequential' else 4
            row = dict(kind=kind, model=name, workers=workers,
                       **timed(lambda: diagnostic(kind, name, values, workers), expected))
            data['diagnostics'].append(row)
            write('benchmark_results.json', data)
            print(f'{kind} {name}: {row["median_s"]:.4f}s', flush=True)


if __name__ == '__main__':
    mp.freeze_support()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('analyze', 'benchmark'), required=True)
    args = parser.parse_args()
    (analyze if args.stage == 'analyze' else benchmark)()
