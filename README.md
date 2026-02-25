---
title: README
created: '2026-02-25T13:01:50.747Z'
modified: '2026-02-25T13:07:50.482Z'
---

# Endfield Timer | 《明日方舟：终末地》BOSS战计时器

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green?style=flat-square&logo=opencv)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square&logo=windows)
![Status](https://img.shields.io/badge/Status-Beta-orange?style=flat-square)
[![Bilibili](https://img.shields.io/badge/Bilibili-%E6%B2%90%E5%85%AE%E7%AB%B9-fb7299?style=flat-square&logo=bilibili&logoColor=white)](https://space.bilibili.com/362473917)

> **基于 Python + OpenCV 实现的 BOSS 战计时工具**

---

## 主要功能 (Features)

* **多 BOSS 适配**
    适配当前版本【危境再现(RE-Crisis)】的三位首领。进入副本前，只需在 UI 界面点击即可一键切换：
    * `罗丹 (Rhodagn)`
    * `三位一体 (Triaggelos)`
    * `白垩界卫 (Marble Aggelomoirai)`

* **底层为图像识别**
    不读取内存，不注入游戏。完全基于**画面特定 UI 像素的状态变化**作为判断战斗起止的核心依据，判定极度轻量且精准。
    
    > **注意**：**全屏/无边框全屏运行游戏！！！** 本工具的计时逻辑与游戏内“蚀刻章镀层”的内部计时器规则**可能存在细微差异**，但足以作为竞速和获取镀层的高精度辅助参考。

---

## 使用说明 (Usage)

1.  **启动程序**：双击目录下的 `EndfieldTimer.exe`。
2.  **选择目标**：在弹出的 UI 界面中，点击选择当前要挑战的 BOSS。
3.  **自动运行**：保持程序运行，进入游戏。程序将在开战前自动进入 `READY` 状态，并在正式开打瞬间自动执行 **开始 / 暂停 / 结束**。
4.  **重置状态**：单击计时器上的 **时间数字区域**，可一键手动重置为待命状态。
5.  **退出程序**：直接点击计时器 UI 左上角的 **「✕」** 按钮即可完全退出。

---

## 计时规则 (Timing Rules)

本工具的核心逻辑是监测屏幕左上角特定 UI 像素的就绪状态以及结算画面的判定。具体规则如下：

| 状态 | 触发条件 / 场景 | 计时行为 |
| :--- | :--- | :--- |
| **就绪** | 识别到开战前的特定 UI 特征 | **显示 READY** *(等待触发)* |
| **开始** | UI 发生变化，画面切入正式战斗的瞬间 | **瞬间开始计时** |
| **暂停** | 战斗中按下 <kbd>Esc</kbd> 呼出暂停菜单 | **暂停计时** |
| **终止** | 识别到 **“挑战成功”** 或结算字样弹出 | **停止计时**<br>*(内置回溯，自动扣除 UI 弹出延迟的 1.17 秒)* |
| **继续** | 角色释放终结技 (Ult) 的 CG 动画<br>战斗中打开背包/道具栏<br>极限闪避触发的“子弹时间” (慢动作)<br>BOSS 转阶段动画 / 强制互动演出 | **计时继续**<br>*(遵循镀层计时规则)* |

---

## 常见问题 (Troubleshooting)

### 1. 计时器不准 / 没反应 / 没自动进入 READY？
由于本项目基于纯图像识别 (CV)，识别准确率极易受游戏画面的光影特效和分辨率缩放干扰。

**推荐设置方案：**
* **全屏运行游戏！** 且最好设置为 **16:9 比例**分辨率（程序已内置超宽屏等比缩放计算，但核心 UI 需保持 16:9 锚点）。
* 关闭游戏设置中的 **“色差 (Chromatic Aberration)”** 选项。
* 关闭游戏设置中的 **“DLSS 帧生成”** 选项。
* 确保游戏并非以极低分辨率运行，以免 UI 像素模糊导致比对失败。

### 2. 解包体积为什么这么大 (~150MB)？
这是由于为了保证图像识别的精度和性能，打包了完整的 `NumPy` 数据计算库和 `OpenCV` 计算机视觉库。这些依赖项占据了绝大部分体积，属于独立运行的正常现象，无需您额外安装任何环境。

---

## 免责声明 (Disclaimer)

* 本工具仅为粉丝自制辅助软件，开源免费。
* 工具仅通过截图分析画面像素，**绝对不修改游戏数据，不读取游戏内存**。
* 请合理使用，不仅限于用于竞速练习参考。
* 这是本人第一次上传 Git 项目，也是第一回为爱发电，上手一个小工程。代码撰写有 AI 参与，经历了多次逻辑迭代和瘦身，保留了注释，可能规范程度亟需提升（滑跪）。
* 本项目只是粗略地解决了终末地目前没有添置局内计时的问题，希望鹰角能够看到这个问题 awa

---
*Created with ❤️ for Arknights: Endfield Players.*
