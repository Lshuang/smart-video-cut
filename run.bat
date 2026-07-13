@echo off
chcp 65001 >nul
setlocal

REM ============================================
REM  智能剪口播 - 剪映风格 YouTube 视频剪辑
REM ============================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║   智能剪口播 - 剪映风格视频剪辑工具         ║
echo   ║   Smart Cut for YouTube Talking-Head Videos  ║
echo   ╚══════════════════════════════════════════════╝
echo.

if "%~1"=="" (
    echo 用法: run.bat ^<视频文件路径^> [选项]
    echo.
    echo 功能:
    echo   * 智能检测并剪除停顿过长、无声音的片段
    echo   * 自动语音识别 + 章节分割
    echo   * 为每段叠加主题文字标签 (淡入动画)
    echo   * YouTube 风格章节过渡转场页 (含音频特效)
    echo   * 可视化进度条 (叠加在视频上方，标注主题)
    echo   * 自动生成时间轴报告
    echo.
    echo 选项:
    echo   --output, -o ^<路径^>      输出文件路径
    echo   --skip-speech             跳过语音识别
    echo   --no-transition           不生成章节过渡转场
    echo   --no-progress-bar         不生成进度条
    echo   --no-topic-text           不添加段落主题文字
    echo   --silence-threshold ^<dB^>  静音阈值 (默认: -35)
    echo   --min-silence ^<ms^>        最短静音时长 (默认: 800ms)
    echo   --titles "标题1" "标题2"   自定义段落标题
    echo.
    echo 示例:
    echo   run.bat my_video.mp4
    echo   run.bat my_video.mp4 --skip-speech --no-transition
    echo   run.bat my_video.mp4 --titles "开场介绍" "核心操作" "总结"
    echo   run.bat my_video.mp4 --silence-threshold -30 --min-silence 500
    echo.
    pause
    exit /b 1
)

python video_editor.py %*
pause