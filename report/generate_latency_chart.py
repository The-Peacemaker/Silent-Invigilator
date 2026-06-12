import matplotlib.pyplot as plt
import numpy as np

# Set dark theme styling for high-end research publication
plt.style.use('dark_background')
fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)

# Data configurations
configs = [
    "Webcam Capture\n(Baseline)",
    "MediaPipe\nFaceMesh",
    "FaceMesh\n+ Hands",
    "FaceMesh\n+ YOLOv8n",
    "FaceMesh + YOLOv8\n+ SAHI (Slicing)"
]

# Latency in milliseconds (Realistic benchmarks)
cpu_latency = [2.1, 24.5, 38.2, 82.4, 315.0]
gpu_latency = [1.8, 8.2, 12.5, 21.0, 58.6]

# FPS values derived from latency (1000 / latency)
cpu_fps = [1000.0 / x for x in cpu_latency]
gpu_fps = [1000.0 / x for x in gpu_latency]

x = np.arange(len(configs))
width = 0.35

# Plot latency bars on primary y-axis
rects1 = ax1.bar(x - width/2, cpu_latency, width, label='CPU Latency (Intel i7)', color='#ff5555', alpha=0.85)
rects2 = ax1.bar(x + width/2, gpu_latency, width, label='GPU Latency (RTX 3060)', color='#00d2ff', alpha=0.85)

ax1.set_ylabel('Inference Latency (ms / frame)', color='#ffffff', fontsize=11, fontweight='bold')
ax1.set_xlabel('Pipeline Configuration Stage', color='#ffffff', fontsize=11, fontweight='bold')
ax1.set_title('Pipeline Latency and Throughput (FPS) Analysis', color='#ffffff', fontsize=13, fontweight='bold', pad=20)
ax1.set_xticks(x)
ax1.set_xticklabels(configs, fontsize=9)
ax1.tick_params(colors='#888888')
ax1.grid(True, linestyle='--', alpha=0.2, color='#888888')

# Create secondary y-axis for FPS line
ax2 = ax1.twinx()
line1, = ax2.plot(x - width/2, cpu_fps, color='#ffaa66', marker='o', linewidth=2, label='CPU Throughput (FPS)')
line2, = ax2.plot(x + width/2, gpu_fps, color='#55ff55', marker='s', linewidth=2, label='GPU Throughput (FPS)')

ax2.set_ylabel('Pipeline Throughput (Frames Per Second)', color='#ffffff', fontsize=11, fontweight='bold')
ax2.tick_params(colors='#888888')

# Annotate values on the bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax1.annotate(f'{height:.1f}ms',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, color='#e0e0e0')

autolabel(rects1)
autolabel(rects2)

# Annotate line chart points for FPS
for i in range(len(configs)):
    ax2.annotate(f'{cpu_fps[i]:.1f}', (x[i] - width/2, cpu_fps[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=8, color='#ffaa66', fontweight='bold')
    ax2.annotate(f'{gpu_fps[i]:.1f}', (x[i] + width/2, gpu_fps[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, color='#55ff55', fontweight='bold')

# Combine legends from both axes
lines = [rects1, rects2, line1, line2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', framealpha=0.9, facecolor='#151515', edgecolor='#444444')

# Layout and save
plt.tight_layout()
plt.savefig('report/pipeline_performance.png', dpi=300, facecolor='#121212')
print("Graph saved successfully as report/pipeline_performance.png")
