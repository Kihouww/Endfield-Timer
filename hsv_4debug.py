import cv2
import numpy as np

def analyze_global_hsv(image_path):
    # 1. 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误：无法找到文件 {image_path}")
        return

    # 2. 转换为 HSV
    # OpenCV定义 -> H: 0-179, S: 0-255, V: 0-255
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 3. 获取所有像素数据（不做任何过滤，包含背景）
    h = img_hsv[:, :, 0].flatten()
    s = img_hsv[:, :, 1].flatten()
    v = img_hsv[:, :, 2].flatten()

    print(f"=== 全局 HSV 范围分析报告 ===")
    print(f"文件路径: {image_path}")
    print(f"图片尺寸: {img.shape[1]}x{img.shape[0]}")
    print(f"总像素数: {len(h)}")
    print("=" * 40)

    # 4. 计算统计数据
    # H (色相)
    h_min, h_max, h_mean = np.min(h), np.max(h), np.mean(h)
    # S (饱和度)
    s_min, s_max, s_mean = np.min(s), np.max(s), np.mean(s)
    # V (亮度)
    v_min, v_max, v_mean = np.min(v), np.max(v), np.mean(v)

    # 5. 输出结果
    print(f"【H - 色相 (0-179)】")
    print(f"  范围: [{h_min}, {h_max}]")
    print(f"  平均: {h_mean:.2f}")
    
    print(f"\n【S - 饱和度 (0-255)】")
    print(f"  范围: [{s_min}, {s_max}]")
    print(f"  平均: {s_mean:.2f}")

    print(f"\n【V - 亮度 (0-255)】")
    print(f"  范围: [{v_min}, {v_max}]")
    print(f"  平均: {v_mean:.2f}")
    print("=" * 40)

    # 6. 给代码编写者的建议
    print("建议阈值写法 (Python):")
    # 为了防止边缘误差，通常建议在 Min 基础上 -5，在 Max 基础上 +5
    # 注意不要越界 (H<0 或 H>179, S/V > 255)
    safe_h_min = max(0, h_min - 2)
    safe_h_max = min(179, h_max + 2)
    safe_s_min = max(0, s_min - 10) # 饱和度建议放宽一点
    safe_s_max = min(255, s_max + 10)
    safe_v_min = max(0, v_min - 10) # 亮度建议放宽一点
    safe_v_max = min(255, v_max + 10)

    print(f"lower_val = np.array([{safe_h_min}, {safe_s_min}, {safe_v_min}])")
    print(f"upper_val = np.array([{safe_h_max}, {safe_s_max}, {safe_v_max}])")

if __name__ == "__main__":
    # 请修改为你要分析的图片文件名
    analyze_global_hsv("Rfinish.png")