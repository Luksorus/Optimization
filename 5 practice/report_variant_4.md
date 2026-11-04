# Практическое занятие 5

## Кэширование с ограничениями инвалидацией и анализом компромиссов

**Дисциплина:** Оптимизация программного кода  
**Вариант:** 4  
**Тема:** Оптимизация рекурсивного комбинаторного сервиса  
**Дата:** 4 ноября 2026 года

## 1. Цель работы

Ускорить вычисления `CombinatorialService`, ограничить размер кэша и обеспечить корректность после изменения `modifier`. Реализованы две стратегии: стандартный LRU и ручной FIFO. Рабочей выбрана LRU: в проведённых замерах она быстрее FIFO и требует меньше кода.

Структура отчёта соответствует заданию и примеру ОПК5. Численные результаты получены запуском программы; измерения и выводы из примера не перенесены как установленные факты.

## 2. Анализ исходного кода и паттернов доступа

Сервис вычисляет рекуррентную функцию при фиксированном модификаторе `m`:

```text
F(n, k, m) = 0,                                  k < 0 или k > n;
F(n, k, m) = m,                                  k = 0 или k = n;
F(n, k, m) = F(n-1, k-1, m) + m * F(n-1, k, m),  иначе.
```

При `m = 1` это биномиальные коэффициенты. После изменения `m` подмена вычислений на `math.comb` уже не сохраняет результат. Порядок сложения и умножения в реализации сохранён, включая поведение чисел с плавающей точкой.

Без кэша одни и те же подзадачи вычисляются многократно. Для допустимых `0 <= k <= n` дерево содержит `2 * C(n,k) - 1` вызовов. Общая верхняя оценка времени — `O(2^n)`, но при фиксированном малом `k` рост определяется `C(n,k)`, поэтому называть любую нагрузку экспоненциальной неточно. Глубина стека — `O(n)`.

В демонстрации генерируются 40 пар, затем добавляются первые 20: получается 60 запросов. Добавленная треть итогового списка гарантированно повторяется; случайная генерация создаёт дополнительные совпадения. Для seed=42 получено:

| max_n | Всего запросов первой фазы | Уникальные внешние пары | Уникальные состояния с подзадачами |
|---:|---:|---:|---:|
| 14 | 60 | 20 | 75 |
| 16 | 60 | 25 | 93 |
| 18 | 60 | 28 | 98 |

Затем `modifier` меняется с `1.0` на `1.1`, и выполняются ещё 20 запросов. Все сохранённые результаты относятся к прежнему состоянию и должны быть удалены.

## 3. Проектирование стратегий

### 3.1 Стандартный LRU

`LRUService` использует `functools.lru_cache(maxsize=256)`. Логический ключ — `(n, k)`, значение — вычисленный `float`. Обёртка создаётся отдельно для каждого экземпляра, поэтому состояние другого сервиса в ключ включать не требуется. При заполнении удаляется наименее недавно использованный ключ; попадание обновляет его приоритет.

Лимит 256 выбран с запасом относительно 98 состояний первой фазы при `max_n=18`. Даже если запросить все допустимые пары при `0 <= n <= 18`, их будет `(19 * 20) / 2 = 190`. Важно учитывать внутренние подзадачи, а не только внешние запросы.

### 3.2 Ручной FIFO

`FIFOService` использует `OrderedDict`, тот же ключ и тот же лимит 256 записей. При переполнении удаляется запись, добавленная раньше остальных: `popitem(last=False)`. Попадание порядок не меняет. Это другая политика вытеснения, а не повторная реализация LRU.

Проверка лимита выполняется после рекурсивного вычисления: рекурсия могла добавить записи во время обработки промаха. Число хранимых записей не превышает лимит. Лимит записей не является строгим лимитом памяти в байтах: дополнительно существуют контейнер, ключи, результаты, стек и временные объекты.

### 3.3 Инвалидация и ограничения

У обоих сервисов изменение `modifier` полностью очищает кэш и счётчики. Свойство `modifier` перехватывает как `set_modifier(value)`, так и прямое присваивание `svc.modifier = value`. Очистка выполняется даже при повторной установке того же значения: это простая консервативная политика. Старые поколения данных не занимают кэш.

```python
@property
def modifier(self):
    return self._modifier

@modifier.setter
def modifier(self, value):
    self._modifier = value
    self.clear_cache()
```

При достаточной вместимости каждое достижимое состояние вычисляется один раз: время одной фазы `O(U + Q)`, память кэша `O(min(U, M))`, стек `O(n)`, где `U` — число состояний, `Q` — число внешних запросов, `M` — лимит. При маленьком лимите вытеснение вызывает повторные вычисления и эта оценка времени уже не гарантируется.

Сервисы предназначены для однопоточного использования и целочисленных `n`, `k` в пределах допустимой глубины рекурсии Python. Потокобезопасность внутреннего LRU не делает изменение `modifier` атомарным относительно всего вычисления. Для очень больших `n` потребуется итеративный алгоритм; кэш не устраняет предел глубины рекурсии. `make_pairs` использует локальный генератор: последовательность пар сохранена, но глобальное состояние `random` больше не сбрасывается. Численные результаты исходного интерфейса сохранены.

## 4. Методика измерений

Среда: Python `3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]`, `Windows-11-10.0.26200-SP0`; процессор `Intel64 Family 6 Model 186 Stepping 2, GenuineIntel`.

Для каждой комбинации выполнено 7 независимых запусков с новым сервисом и холодным кэшем. Время — медиана `perf_counter_ns`; дополнительно приведён диапазон минимум–максимум. Время включает создание сервиса, обе фазы вычисления, смену состояния и очистку кэша. Генерация входных данных и предварительный `gc.collect()` не входят в интервал. Это полный сценарий, тогда как третье поле исходной `run_task` измеряет только первую фазу.

Память измерена отдельным запуском с `tracemalloc`: показаны пиковые и оставшиеся отслеживаемые выделения Python от создания сервиса до завершения нагрузки. Входной список подготовлен заранее и не включён. Это не RSS процесса и не исключительно размер кэша. Память измерялась один раз для каждой комбинации. Временные замеры выполнены без `tracemalloc`.

Сценарии:

- `max_n=14/16/18`: 60 запросов с повторами, инвалидация и ещё 20 запросов.
- `unique_base`: 2000 уникальных пар `(n, 0)`, затем инвалидация и первые 20 пар. Во всех случаях вычисление базовое; внутри каждой фазы повторов нет.
- `invalidate_each`: 60 запросов `(10, 3)` с установкой модификатора перед каждым запросом, попеременно `1.0` и `1.1`. Внутренние подзадачи одного запроса всё ещё могут повторяться.

В каждом измерении проверяется точное совпадение результата с исходной реализацией. Порядок стратегий фиксирован, процесс не изолирован от фоновой нагрузки Windows. Значения менее миллисекунды особенно чувствительны к шуму; коэффициенты описывают этот запуск, а не универсальную гарантию.

## 5. Результаты измерений

| Сценарий | Стратегия | Медиана, мс | Мин–макс, мс | Ускорение к исходному | Пик, КиБ | Осталось, КиБ |
|---|---|---:|---:|---:|---:|---:|
| max_n=14 | Без кэша | 4.2331 | 4.0629–4.3469 | 1.00× | 1.27 | 0.64 |
| max_n=14 | LRU | 0.0547 | 0.0506–0.0967 | 77.39× | 13.74 | 13.12 |
| max_n=14 | FIFO | 0.0891 | 0.0819–0.1391 | 47.51× | 14.31 | 11.91 |
| max_n=16 | Без кэша | 8.8844 | 8.3566–10.8976 | 1.00× | 1.23 | 0.61 |
| max_n=16 | LRU | 0.0670 | 0.0628–0.1199 | 132.60× | 20.23 | 17.62 |
| max_n=16 | FIFO | 0.1066 | 0.1016–0.1275 | 83.34× | 19.64 | 17.27 |
| max_n=18 | Без кэша | 18.7122 | 17.9109–19.1344 | 1.00× | 1.18 | 0.55 |
| max_n=18 | LRU | 0.0701 | 0.0628–0.0925 | 266.94× | 20.55 | 18.38 |
| max_n=18 | FIFO | 0.1142 | 0.1081–0.2062 | 163.85× | 20.90 | 17.70 |
| unique_base | Без кэша | 0.1200 | 0.1131–0.1249 | 1.00× | 0.84 | 0.22 |
| unique_base | LRU | 0.4175 | 0.3953–0.5251 | 0.29× | 65.80 | 17.02 |
| unique_base | FIFO | 0.9651 | 0.8874–1.4345 | 0.12× | 67.31 | 15.96 |
| invalidate_each | Без кэша | 0.7646 | 0.7446–0.8359 | 1.00× | 0.49 | 0.34 |
| invalidate_each | LRU | 0.3976 | 0.3874–0.4441 | 1.92× | 6.50 | 6.28 |
| invalidate_each | FIFO | 0.8150 | 0.7735–0.8581 | 0.94× | 8.34 | 5.53 |

### Графики сравнения

Текстовые столбчатые графики встроены в Markdown и не требуют внешних изображений. Указанные справа числа точнее длины полос; шкала каждого графика независима.

**Ускорение на повторяющихся запросах** (один `#` ≈ 10×; больше — лучше):

```text
max_n=14 LRU  ######## 77.4x
max_n=14 FIFO ##### 47.5x
max_n=16 LRU  ############# 132.6x
max_n=16 FIFO ######## 83.3x
max_n=18 LRU  ########################### 266.9x
max_n=18 FIFO ################ 163.9x
```

**Пиковая память при max_n=18** (один `#` ≈ 1 КиБ; меньше — лучше):

```text
Без кэша   # 1.18 КиБ
LRU        ##################### 20.55 КиБ
FIFO       ##################### 20.90 КиБ
```

**Время на уникальных базовых запросах** (один `#` ≈ 0.05 мс; меньше — лучше):

```text
Без кэша   ## 0.1200 мс
LRU        ######## 0.4175 мс
FIFO       ################### 0.9651 мс
```

При `max_n=18` LRU ускоряет весь сценарий в 266.94 раза, FIFO — в 163.85 раза. Пиковая отслеживаемая память растёт с 1.18 КиБ до 20.55 и 20.90 КиБ соответственно. На этой нагрузке обе стратегии вмещают все подзадачи, поэтому их разные политики вытеснения почти не проявляются; основное различие времени связано с накладными расходами реализации. Поведение при вытеснении проверено отдельным тестом с лимитом 2.

После последней инвалидации и выполнения 20 запросов при `max_n=18` обе стратегии имеют 97 записей, 77 попаданий и 97 промахов: доля попаданий 44.25%. Эти счётчики включают внутреннюю рекурсию и относятся только ко второй фазе: инвалидация сбрасывает первую. Поэтому их нельзя трактовать как долю повторных внешних запросов за весь сценарий.

### Когда кэш бесполезен

На `unique_base` попаданий нет даже среди внутренних вычислений: каждый вызов сразу возвращает модификатор. LRU медленнее исходного варианта в 3.48 раза, FIFO — в 8.04 раза; пик памяти составляет 65.80 и 67.31 КиБ против 0.84 КиБ. Достаточно хранить только 256 записей, чтобы накладные расходы были заметны; ограниченный кэш не означает бесплатный кэш.

Уникальность внешних пар сама по себе не доказывает бесполезность кэша: рекурсивные подзадачи могут совпадать. Поэтому выбран именно поток базовых случаев.

При инвалидации перед каждым небазовым запросом LRU всё ещё ускоряет вычисления примерно в 1.92 раза за счёт внутренних повторов. FIFO на этом сценарии немного медленнее исходного варианта (0.8150 против 0.7646 мс). Частые изменения состояния существенно сокращают пользу повторного использования.

## 6. Проверка корректности

Запуск `python variant_4_optimized.py --test` завершился успешно: **6 тестов, OK**.

| Тест | Что проверено |
|---|---|
| `test_equivalence_and_state_changes` | Точное равенство исходной функции при `n=-1..10`, граничных и недопустимых `k`; модификаторах `1.0`, `1.1`, `0.0`, `-0.5`, `2.0`, затем `1.0`; лимитах 1, 8, 256; очистка прогретого кэша и счётчиков |
| `test_repeated_queries` | Повтор `(18,6)` даёт попадание без нового промаха |
| `test_instance_isolation` | Изменение одного сервиса не очищает кэш другого |
| `test_eviction_policy` | LRU сохраняет недавно прочитанный ключ, FIFO удаляет раньше добавленный; лимит 2 |
| `test_original_scenarios` | Совпадение двух сумм для `max_n=14,16,18` |
| `test_capacity_validation` | Отклонение нулевого, отрицательного и нецелого лимита |

Дополнительно отдельно импортирован предоставленный файл из Temp и непосредственно сопоставлены результаты его `run_task` с оптимизированной версией:

| max_n | Первая сумма | Сумма после modifier=1.1 | Совпадение |
|---:|---:|---:|---|
| 14 | 26325.00 | 16853.48 | Да |
| 16 | 55797.00 | 40717.56 | Да |
| 18 | 120155.00 | 106183.29 | Да |

Временное поле не сравнивается на равенство: оно меняется после оптимизации. При округлении до 4 знаков быстрый запуск может выводить `0.0` секунды; для сравнения используется отдельный измеритель в миллисекундах.

## 7. Анализ компромиссов и выбор решения

| Критерий | Без кэша | LRU | FIFO |
|---|---|---|---|
| Повторные подзадачи | Вычисляются заново | Переиспользуются | Переиспользуются |
| Ограничение памяти | Только стек и временные значения | 256 записей плюс служебная память | 256 записей плюс служебная память |
| Вытеснение | Нет | Наименее недавно использованный ключ | Раньше добавленный ключ |
| Сложность реализации | Низкая | Низкая, стандартная библиотека | Выше, ручные счётчики и вытеснение |
| Инвалидация | Не требуется | Полная очистка при изменении свойства | Полная очистка при изменении свойства |
| Поведение на данной повторной нагрузке | Самое медленное | Самое быстрое | Быстрее исходного, медленнее LRU |

Выбрана **LRUService**, доступная под исходным именем `CombinatorialService`. Она обеспечивает наилучшее время на измеренной основной нагрузке, ограниченную вместимость и простую инвалидацию. Ручной FIFO стоит выбирать при явном требовании удалять записи по возрасту поступления или при необходимости расширять политику хранения. В представленном эксперименте оснований считать ручной словарь быстрее стандартного LRU нет.

Обе стратегии требуют тестировать все способы изменения состояния. Если для многопоточного приложения понадобится одновременная смена модификатора и вычисление, потребуется синхронизация всей операции либо неизменяемое состояние, включённое в ключ.

Кэш полезен при дорогих повторяющихся вычислениях и достаточно долгом сроке жизни состояния. Для дешёвых уникальных запросов лучше оставить вычисление без кэша. При больших `n` следует перейти к итеративному динамическому программированию: оно устраняет рекурсивный стек и позволяет хранить один ряд. Для постоянного `modifier=1` можно рассмотреть `math.comb`; для произвольного модификатора необходимо сохранить исходную рекуррентную зависимость. Это отдельные алгоритмические изменения, требующие собственной проверки.

## 8. Запуск и воспроизводимость

Все варианты и тесты включены в один файл; внешних зависимостей нет. Из каталога с файлом:

```powershell
python variant_4_optimized.py
python variant_4_optimized.py --test
python variant_4_optimized.py --benchmark
```

По умолчанию выводится исходный демонстрационный формат с двумя суммами и временем первой фазы. `--benchmark` печатает JSON с необработанными измерениями, средой запуска и статистикой последней фазы. Повторный запуск даст другие времена при сохранении вычисленных сумм.

## 9. Полный код всех вариантов и автоматических тестов

Ниже приведено содержимое отдельного файла `variant_4_optimized.py`, включая исходную рекурсию, LRU, FIFO, тесты и измеритель.

```python
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
```
