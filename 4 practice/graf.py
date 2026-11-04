import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

# 1. Точные данные из наших замеров tracemalloc
N_values = [50_000, 100_000, 200_000]

# Пиковая память исходного кода (МБ)
memory_before = [17.6139, 35.0897, 70.3860]

# Пиковая память оптимизированного кода (МБ)
memory_after = [0.0001, 0.0001, 0.0001]

# 2. Настройка внешнего вида (высокое разрешение для Word, как в 3-й практике)
plt.figure(figsize=(10, 6), dpi=300)

# 3. Построение линий с фирменными стилями
plt.plot(N_values, memory_before, 
         marker='o', 
         label='До оптимизации (O(N))', 
         color='#d62728',     # Красный
         linewidth=2, 
         markersize=8)

plt.plot(N_values, memory_after, 
         marker='s', 
         label='После оптимизации (O(1))', 
         color='#2ca02c',     # Зеленый
         linewidth=2, 
         markersize=8)

# 4. Оформление осей и заголовков
plt.title('Сравнение пикового потребления памяти', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Размер данных (N)', fontsize=12)
plt.ylabel('Пиковая память (МБ)', fontsize=12)

# Принудительно задаем значения на оси X
plt.xticks(N_values)

# 5. ЛОГАРИФМИЧЕСКАЯ ШКАЛА для оси Y (критически важно для разницы в 40 000 раз)
plt.yscale('log')

# Форматирование подписей оси Y, чтобы они были обычными числами, а не 1e2
ax = plt.gca()
ax.yaxis.set_major_formatter(ScalarFormatter())
ax.yaxis.get_major_formatter().set_scientific(False)

# 6. Сетка и легенда
plt.grid(True, linestyle='--', alpha=0.7, which="both") # which="both" рисует сетку и для минорных тиков лога
plt.legend(fontsize=11, loc='upper left')

# 7. Добавляем точные значения прямо на точки (как в 3-й практике)
for i, txt in enumerate(memory_before):
    plt.annotate(f"{txt} МБ", 
                 (N_values[i], memory_before[i]), 
                 textcoords="offset points", 
                 xytext=(0, 12), 
                 ha='center', 
                 fontsize=9, 
                 color='#d62728',
                 fontweight='bold')

for i, txt in enumerate(memory_after):
    plt.annotate(f"{txt} МБ", 
                 (N_values[i], memory_after[i]), 
                 textcoords="offset points", 
                 xytext=(0, -15), 
                 ha='center', 
                 fontsize=9, 
                 color='#2ca02c',
                 fontweight='bold')

# 8. Сохранение в файл и отображение
filename = 'memory_comparison.png'
plt.savefig(filename, bbox_inches='tight')
print(f"✅ График успешно сохранен в файл: {filename}")

plt.show()