# MousePanPaper

鼠标跟随视差滚动壁纸 — mpvpaper 增强工具  
Mouse-following parallax wallpaper — mpvpaper enhancement tool

---

## 简介 / Introduction

MousePanPaper 监听鼠标位置，实时调整 mpvpaper 壁纸的 `video-pan-x/y`，实现鼠标移动时壁纸跟随偏移的视差效果。支持缩放、平滑缓动、全屏自动禁用、动态模糊。

MousePanPaper listens to mouse position and adjusts mpvpaper's `video-pan-x/y` in real time, creating a parallax effect where the wallpaper follows the cursor. Supports zoom, smooth easing, auto-disable on fullscreen, and motion blur.

---

## 依赖 / Dependencies

- [Hyprland](https://hyprland.org/)
- [mpvpaper](https://github.com/GhostNaN/mpvpaper)
- Python 3.10+

---

## 安装 / Installation

```bash
# 克隆或复制脚本到本地 / Clone or copy the script locally
cp MousePanPaper.py ~/.config/hypr/scripts/
```

---

## 配置 / Configuration

将以下内容添加到你的 Hyprland 配置文件 (`~/.config/hypr/hyprland.conf`)：

Add the following to your Hyprland config (`~/.config/hypr/hyprland.conf`):

```conf
exec-once = sleep 1 && python3 ~/.config/hypr/scripts/MousePanPaper.py -i 1 -m 0.03
```

> `sleep 1` 等待 mpvpaper 初始化完成 / waits for mpvpaper to finish initializing.

---

## 参数 / Options

| 参数 / Argument | 说明 / Description | 默认 / Default |
|---|---|---|
| `-i`, `--interval` | 渲染间隔 (ms) / Render interval (ms) | `16` |
| `-m`, `--max-pan` | 最大偏移比例 / Max pan ratio | `0.015` |
| `-s`, `--smooth` | 平滑系数 0~1 / Smoothing factor 0~1 | `0.08` |
| `-z`, `--zoom` | 壁纸放大倍率 / Wallpaper zoom scale | `1.05` |
| `-p`, `--path` | IPC 套接字路径 / IPC socket path | `/tmp/mpvpaper.sock` |
| `-f`, `--fs-disable` | 全屏时自动禁用 / Disable on fullscreen | `false` |
| `-e`, `--exclude` | 排除的窗口类 (可重复) / Excluded window classes (repeatable) | `kitty` |
| `-b`, `--blur` | 动态模糊 / Motion blur | `false` |
| `--ease` | 缓动曲线 / Easing curve | `in-out` |
| `-d`, `--debug` | 调试输出 / Debug output | `false` |

---

## 使用示例 / Usage Examples

```bash
# 基础用法 / Basic
python3 MousePanPaper.py -i 1 -m 0.03

# 放大 3% + 全屏禁用 / Zoom 3% + disable on fullscreen
python3 MousePanPaper.py -i 1 -m 0.03 -z 1.03 -f

# 排除 Alacritty + 动态模糊 / Exclude Alacritty + blur
python3 MousePanPaper.py -i 1 -m 0.03 -e alacritty -b
```

---

## 说明 / Notes

本项目由 AI 辅助完成。  
This project was AI-assisted.
