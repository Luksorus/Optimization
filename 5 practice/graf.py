"""Графики практики 5 из benchmark_results.json; требуется Matplotlib.

Запуск: python graf.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
STYLES = {
    'OriginalService': ('Без кэша', '#64748b', 'o'),
    'LRUService': ('LRU', '#2563eb', 's'),
    'FIFOService': ('FIFO', '#e87918', '^'),
}


def main():
    data = json.loads((ROOT / 'benchmark_results.json').read_text(encoding='utf-8-sig'))
    rows = {(r['workload'], r['strategy']): r for r in data['rows']}
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False,
                         'axes.spines.right': False})
    sizes = [14, 16, 18]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for strategy, (label, color, marker) in STYLES.items():
        points = [rows[f'max_n={n}', strategy] for n in sizes]
        medians = [r['median_ms'] for r in points]
        errors = [[r['median_ms'] - r['min_ms'] for r in points],
                  [r['max_ms'] - r['median_ms'] for r in points]]
        axes[0].errorbar(sizes, medians, yerr=errors, color=color, marker=marker,
                         capsize=4, label=label, linewidth=2)
        speedups = [rows[f'max_n={n}', 'OriginalService']['median_ms']/t
                    for n, t in zip(sizes, medians)]
        axes[1].plot(sizes, speedups, color=color, marker=marker,
                     label=label, linewidth=2)
        if strategy != 'OriginalService':
            axes[1].annotate(f'{speedups[-1]:.1f}×', (18, speedups[-1]),
                             xytext=(-8, 10), textcoords='offset points',
                             ha='right', color=color)
    for ax in axes:
        ax.set_xticks(sizes)
        ax.set_xlabel('Максимальное n')
        ax.grid(True, alpha=.25)
        ax.legend()
    axes[0].set_yscale('log')
    axes[0].set_ylabel('Время, мс (логарифмическая шкала)')
    axes[0].set_title('Медиана и диапазон min–max')
    axes[1].set_ylabel('Ускорение к исходной версии, раз')
    axes[1].set_title('Запросы с повторениями')
    axes[1].set_ylim(bottom=0)
    fig.savefig(ROOT / 'performance_comparison.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.6), constrained_layout=True)
    for strategy, (label, color, marker) in STYLES.items():
        peaks = [rows[f'max_n={n}', strategy]['peak_bytes']/1024 for n in sizes]
        ax.plot(sizes, peaks, color=color, marker=marker, linewidth=2, label=label)
    ax.set(xticks=sizes, xlabel='Максимальное n', ylabel='Пиковая память, КиБ',
           title='Цена кэширования: отслеживаемая память Python')
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=.25)
    ax.legend()
    fig.savefig(ROOT / 'memory_comparison.png', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    workloads = ['unique_base', 'invalidate_each']
    labels = ['Уникальные\nбазовые запросы', 'Инвалидация\nперед каждым запросом']
    width = .24
    for offset, (strategy, (label, color, _)) in zip((-.24, 0, .24), STYLES.items()):
        points = [rows[w, strategy] for w in workloads]
        xs = [i+offset for i in range(2)]
        medians = [r['median_ms'] for r in points]
        errors = [[r['median_ms'] - r['min_ms'] for r in points],
                  [r['max_ms'] - r['median_ms'] for r in points]]
        bars = axes[0].bar(xs, medians, width, yerr=errors, capsize=3,
                           color=color, label=label)
        axes[0].bar_label(bars, labels=[f'{v:.3f}' for v in medians],
                          padding=3, fontsize=9)
        bars = axes[1].bar(xs, [r['peak_bytes']/1024 for r in points], width,
                           color=color, label=label)
        axes[1].bar_label(bars, fmt='%.2f', padding=3, fontsize=9)
    for ax in axes:
        ax.set_xticks([0, 1], labels)
        ax.grid(axis='y', alpha=.25)
        ax.set_axisbelow(True)
        ax.legend(loc='upper right', fontsize=9)
        ax.margins(y=.24)
    axes[0].set(ylabel='Время, мс', title='Когда кэш не окупается')
    axes[1].set(ylabel='Пиковая память, КиБ', title='Расходы на хранение и обслуживание')
    fig.savefig(ROOT / 'cache_tradeoffs.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
