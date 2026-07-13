# 智能剪口播 (Smart Video Cut)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 剪映风格的智能视频剪辑工具，专为 YouTube 口播视频设计。一键完成静音剪除、章节分割、转场动画、进度条叠加全流程。

## ✨ 功能亮点

- **智能静音检测** — 自适应阈值，自动找到最佳切割点，精准剪除停顿过长、无声音的片段
- **语音识别分段** — 基于 faster-whisper 自动转录，智能分割为章节，自动生成主题
- **YouTube 风格转场** — 深色背景 + 章节编号 + 标题 + 时长信息 + 音效 (whoosh + 叮)
- **可视化进度条** — 叠加在视频上方，标注各章节主题，随时间填充
- **段落主题文字** — 每段底部叠加主题标签，支持淡入动画
- **音频特效** — 转场音效，增强章节过渡的听觉体验

## 🎬 处理流程

```
步骤1: 智能静音检测 → 自适应阈值找到最佳切割点
步骤2: 语音识别 → faster-whisper 转录 + 章节分割
步骤3: 视频切割 → 按段落精确切割
步骤4: 主题文字 → 每段底部叠加主题标签
步骤5: 章节转场 → 深色背景 + 编号 + 标题 + 音效
步骤6: 视频拼接 → 转场 + 段落拼接
步骤7: 进度条 → 顶部可视化进度条 + 章节标签
步骤8: 叠加合成 → 最终输出
```

## 📦 安装

```bash
# 安装依赖
pip install pydub numpy Pillow faster-whisper

# 安装技能
npx skills add <username>/smart-video-cut
```

**前置要求：** FFmpeg 需已安装，路径在 `config.py` 中配置。

## 🚀 快速使用

```bash
cd video_editor_tool

# 基础用法
python video_editor.py 输入视频.mp4

# 全部功能：静音剪除 + 转场 + 进度条 + 主题文字
python video_editor.py my_video.mp4

# 自定义段落标题
python video_editor.py my_video.mp4 --titles "开场介绍" "核心操作" "总结回顾"

# 仅剪静音（速度最快）
python video_editor.py my_video.mp4 --skip-speech --no-transition --no-progress-bar --no-topic-text

# 调整静音检测灵敏度
python video_editor.py my_video.mp4 --silence-threshold -30 --min-silence 500
```

## 📋 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output, -o` | 输出视频路径 | `output/<name>_smartcut.mp4` |
| `--skip-speech` | 跳过语音识别 | 关闭 |
| `--no-transition` | 不生成章节转场 | 关闭 |
| `--no-progress-bar` | 不生成进度条 | 关闭 |
| `--no-topic-text` | 不添加主题文字 | 关闭 |
| `--silence-threshold` | 静音阈值 (dB) | -35 |
| `--min-silence` | 最短静音时长 (ms) | 800 |
| `--titles` | 自定义段落标题 | 自动生成 |

## 🏗 模块架构

| 模块 | 文件 | 功能 |
|------|------|------|
| 配置 | `config.py` | 全局参数：阈值、颜色、字体、编码 |
| 静音检测 | `silence_detector.py` | pydub 静音检测 + 自适应阈值 + 视频切割 |
| 语音识别 | `speech_to_text.py` | faster-whisper 转录 + 章节自动分割 |
| 文字叠加 | `text_overlay.py` | FFmpeg drawtext 段落主题标签 |
| 转场动画 | `chapter_transition.py` | PIL 逐帧生成 YouTube 风格转场页 |
| 进度条 | `progress_bar.py` | PIL 逐帧生成可视化进度条 |
| 音频特效 | `audio_effects.py` | 转场音效 (whoosh + 叮声) |
| 主编排器 | `video_editor.py` | 8步流水线整合 |
| 测试脚本 | `test_tool.py` | 端到端测试验证 |

## ⚙️ 配置

在 `config.py` 中可调整：

- **静音检测**: `SILENCE_THRESHOLD_DB` (-35), `SILENCE_MIN_DURATION_MS` (800)
- **语音识别**: `WHISPER_MODEL` (medium), `WHISPER_LANGUAGE` (zh)
- **进度条外观**: `PROGRESS_BAR_HEIGHT` (60), `PROGRESS_BAR_FILL_COLOR` (红色)
- **转场动画**: `TRANSITION_DURATION_SEC` (2.5), `TRANSITION_BG_COLOR` (深蓝黑)
- **视频编码**: `OUTPUT_FPS` (30), `OUTPUT_CRF` (20)

## 📄 输出

| 文件 | 位置 |
|------|------|
| 最终视频 | `output/<name>_smartcut.mp4` |
| 时间轴报告 | `output/timeline_report.txt` |
| 临时文件 | `temp/` (可手动清理) |

## 📝 License

MIT