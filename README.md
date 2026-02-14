# Endfield Timer | 《明日方舟：终末地》BOSS战计时器

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green?style=flat-square&logo=opencv)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square&logo=windows)
![Status](https://img.shields.io/badge/Status-Beta-orange?style=flat-square)

> **基于 Python + OpenCV 实现的图像识别 BOSS 战计时工具**

---

## 主要功能 (Features)

* **多 BOSS 适配**
    适配当前版本【危境再现(RE-Crisis)】的三位首领。进入副本前，只需在 UI 界面点击即可一键切换：
    * `罗丹 (Rhodagn)`
    * `三位一体 (Triaggelos)`
    * `白垩界卫 (Marble Aggelomoirai)`

* **纯图像识别计时**
    不读取内存，不注入游戏。完全基于**BOSS血条的 UI 像素变化**作为判断战斗时长的核心依据。
    
    > **注意**：全屏运行游戏！！！本工具的计时逻辑与游戏内“蚀刻章镀层”的内部计时器规则**可能存在细微差异**，但足以作为是否能获取镀层的辅助参考。

---

## 使用说明 (Usage)

1.  **启动程序**：双击目录下的 `Launch_EndfieldTimer.bat`。
2.  **选择目标**：在弹出的 UI 界面中，点击选择当前要挑战的 BOSS。
3.  **自动运行**：保持程序运行，进入游戏战斗。计时器将根据画面自动执行 **开始 / 暂停 / 结束**。
4.  **重置状态**：单击计时器上的 **数字区域**，可一键重置为待命状态。
5.  **退出程序**：当计时器窗口处于焦点（选中）状态时，按下键盘上的 <kbd>Delete</kbd> 键即可完全退出。

---

## 计时规则 (Timing Rules)

本工具的核心逻辑是监测屏幕上方 BOSS 血条的**出现与消失**。具体判定矩阵如下：

| 状态 | 触发条件 / 场景 | 计时行为 |
| :--- | :--- | :--- |
| **开始** | 屏幕最上方**识别到 BOSS 血条**出现 | **开始计时** |
| **暂停** | 战斗中按下 <kbd>Esc</kbd> 暂停菜单<br>BOSS 进入**转阶段过渡动画** | **暂停计时** |
| **终止** | 识别到 **“挑战成功”** 字样弹出 | **停止计时**<br>*(自动回溯至血条消失瞬间)* |
| **继续** | 角色释放终结技 (Ult) 的 CG 动画<br>战斗中打开背包/道具栏<br>极限闪避触发的“子弹时间” (慢动作)<br>无“跳过”选项的 BOSS 强制互动动画 | **计时继续**<br>*(不停止/不放缓)* |

> **智能回溯**：当检测到战斗胜利时，程序会自动扣除从“血条消失”到“结算字样弹出”之间的 UI 延迟时间，确保最终成绩尽可能接近真实的击杀时间。

---

## 常见问题 (Troubleshooting)

### 1. 计时器不准 / 没反应 / 过场不暂停？
由于本项目基于纯图像识别 (CV)，识别准确率极易受游戏画面的光影特效干扰。
**推荐解决方案：**
* 关闭游戏设置中的 **“色差 (Chromatic Aberration)”** 选项。
* 关闭游戏设置中的 **“DLSS 帧生成”** 选项。
* 确保游戏并非以极低分辨率运行，以免 UI 模糊无法识别。

### 2. 软件体积为什么这么大 (166MB)？
这是由于为了保证图像识别的精度和性能，打包了完整的 `NumPy` 数据计算库和 `OpenCV` 计算机视觉库。这些依赖项占据了绝大部分体积，属于正常现象。

---

## 免责声明 (Disclaimer)

* 本工具仅为粉丝自制辅助软件，开源免费。
* 工具仅通过截图分析画面，**不修改游戏数据，不读取游戏内存**。
* 请合理使用，不仅限于用于竞速练习参考。
* 这是本人第一次上传git项目，也是第一回为爱发电，上手一个小工程。代码撰写有vibe coding参与，保留了注释，可能规范程度亟需提升（滑跪）。

---
*Created with ❤️ for Arknights: Endfield Players.*