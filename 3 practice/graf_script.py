import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

# 1. Точные данные с точностью до миллионных (6 знаков после запятой)
N_values = [ 40, 60, 80]
time_before = [0.0125, 0.0429, 0.1015]  # Исходный код
time_after = [0.001493, 0.002808, 0.003775]

# 2. Настройка внешнего вида графика (высокое разрешение для Word)
plt.figure(figsize=(10, 6), dpi=300)

# 3. Построение линий
plt.plot(N_values, time_before, 
         marker='o', 
         label='До оптимизации (чистый Python)', 
         color='#d62728',     # Красный
         linewidth=2, 
         markersize=8)

plt.plot(N_values, time_after, 
         marker='s', 
         label='После оптимизации (NumPy)', 
         color='#2ca02c',     # Зеленый
         linewidth=2, 
         markersize=8)

# 4. Оформление осей и заголовков
plt.title('Зависимость времени выполнения от размера матрицы (N)', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Размер матрицы N', fontsize=12)
plt.ylabel('Время выполнения (секунды)', fontsize=12)

# Принудительно задаем значения на оси X
plt.xticks(N_values)

# 5. ФОРМАТИРОВАНИЕ ОСИ Y: 6 знаков после запятой (миллионные)
ax = plt.gca()
ax.yaxis.set_major_formatter(FormatStrFormatter('%.6f'))

# 6. Сетка и легенда
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=11, loc='upper left')

# Опционально: добавить подписи значений прямо на точки для наглядности
for i, txt in enumerate(time_before):
    plt.annotate(f"{txt:.6f}", (N_values[i], time_before[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, color='#d62728')

for i, txt in enumerate(time_after):
    plt.annotate(f"{txt:.6f}", (N_values[i], time_after[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=8, color='#2ca02c')

# 7. Сохранение в файл и отображение
filename = 'performance_comparison.png'
plt.savefig(filename, bbox_inches='tight')
print(f"✅ График успешно сохранен в файл: {filename}")

plt.show()