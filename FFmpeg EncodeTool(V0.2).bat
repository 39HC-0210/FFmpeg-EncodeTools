@echo off
chcp 65001 >nul
title FFmpeg Tool
setlocal enabledelayedexpansion

set "script_dir=%~dp0"
set "output_folder=%script_dir%Output\"
set "subtitle_dir=%script_dir%Subtitles\"
set "font_dir=%script_dir%Fonts\"

echo 检测并创建必要文件夹...
if not exist "%output_folder%" (
    md "%output_folder%"
    echo 已创建 Output 文件夹：%output_folder%
)
if not exist "%subtitle_dir%" (
    md "%subtitle_dir%"
    echo 已创建 Subtitles 文件夹：%subtitle_dir%
)
if not exist "%font_dir%" (
    md "%font_dir%"
    echo 已创建 Fonts 文件夹：%font_dir%
)
echo.

:mode_select
cls
echo ===================== 视频压制模式选择 =====================
echo 1. 普通压制视频（无内嵌字幕）
echo 2. 压制内嵌字幕的视频
echo ============================================================
set "mode="
set /p "mode=请输入模式编号（1/2）："

if "%mode%"=="1" (
    set "subtitle_flag=0"
    goto encoder_select
) else if "%mode%"=="2" (
    set "subtitle_flag=1"
    goto subtitle_input
) else (
    echo 错误：请输入有效的模式编号（1或2）！
    pause >nul
    goto mode_select
)

:subtitle_input
cls
echo ===================== 内嵌字幕配置 =====================
echo 字幕文件需放在脚本目录下的 Subtitles 文件夹中
echo 请输入ASS字幕文件名（例如：JPTC.ass）
echo ============================================================

echo 当前Subtitles文件夹中的ASS文件：
dir /b /a-d "!subtitle_dir!*.ass" 2>nul
if %errorlevel% equ 1 (
    echo 未找到ASS文件！
)

set "subtitle_file="
set /p "subtitle_file=请输入ASS文件名："

set "full_subtitle_path=Subtitles/!subtitle_file!"
if not exist "!full_subtitle_path!" (
    echo 错误：未在Subtitles文件夹中找到文件「%subtitle_file%」！
    pause >nul
    goto subtitle_input
)
goto encoder_select

:encoder_select
cls
echo ===================== 视频编码器选择 =====================
echo 可选值：
echo - libx264 / 264
echo - libx265 / 265
echo ============================================================
set "encoder="
set /p "encoder=请输入编码器（支持264/265快捷输入）："

if /i "%encoder%"=="264" set "encoder=libx264"
if /i "%encoder%"=="265" set "encoder=libx265"
if /i not "%encoder%"=="libx264" if /i not "%encoder%"=="libx265" (
    echo 错误：请输入有效的编码器（libx264/libx265 或 264/265）！
    pause >nul
    goto encoder_select
)
goto crf_select

:crf_select
cls
echo ===================== CRF值选择 =====================
echo CRF范围：0~51（值越小画质越高，文件越大）
echo.
echo ============================================================
set "crf="
set /p "crf=请输入CRF值（0-51）："

set "crf_num=%crf%"
for /f "delims=0123456789" %%a in ("!crf_num!") do (
    echo 错误：CRF值必须是数字！
    pause >nul
    goto crf_select
)
if !crf_num! lss 0 (
    echo 错误：CRF值必须在0~51之间！
    pause >nul
    goto crf_select
)
if !crf_num! gtr 51 (
    echo 错误：CRF值必须在0~51之间！
    pause >nul
    goto crf_select
)
goto preset_select

:preset_select
cls
echo ===================== Preset选择 =====================
echo 数字快捷输入（1=最慢，9=最快）：
echo 1=veryslow  2=slower  3=slow  4=medium  5=fast
echo 6=faster    7=veryfast 8=superfast 9=ultrafast
echo 也可直接输入预设名（如：medium）
echo ============================================================
set "preset="
set /p "preset=请输入Preset（数字1-9或预设名）："

set "preset_map_1=veryslow"
set "preset_map_2=slower"
set "preset_map_3=slow"
set "preset_map_4=medium"
set "preset_map_5=fast"
set "preset_map_6=faster"
set "preset_map_7=veryfast"
set "preset_map_8=superfast"
set "preset_map_9=ultrafast"

set "is_num=0"
for /f "delims=0123456789" %%a in ("%preset%") do set "is_num=1"
if %is_num%==0 (

    if !preset! lss 1 (
        echo 错误：数字必须在1~9之间！
        pause >nul
        goto preset_select
    )
    if !preset! gtr 9 (
        echo 错误：数字必须在1~9之间！
        pause >nul
        goto preset_select
    )
    call set "preset=!preset_map_%preset%!"
)

set "valid_preset=0"
for %%p in (ultrafast superfast veryfast faster fast medium slow slower veryslow) do (
    if /i "!preset!"=="%%p" set "valid_preset=1"
)
if !valid_preset!==0 (
    echo 错误：Preset输入无效！
    pause >nul
    goto preset_select
)
goto resolution_select

:resolution_select
cls
echo ===================== 分辨率选择 =====================
echo 可选值：
echo - 720 / 0       --缩放到720P
echo - 1080 / 1      --保持原分辨率，不缩放
echo ============================================================
set "resolution="
set /p "resolution=请输入分辨率选项："

if not "%resolution%"=="720" if not "%resolution%"=="0" if not "%resolution%"=="1080" if not "%resolution%"=="1" (
    echo 错误：请输入有效的分辨率选项（720/1080 或 0/1）！
    pause >nul
    goto resolution_select
)

set "scale_param="
if "%resolution%"=="720" set "scale_param=scale=-1:720"
if "%resolution%"=="0" set "scale_param=scale=-1:720"

goto file_select

:file_select
cls
echo ===================== 选择视频文件 =====================
echo 请将需要压制的视频文件拖拽到本窗口，然后按回车
echo ============================================================
set "input_files="
set /p "input_files=请输入/拖拽视频文件："

if not defined input_files (
    echo 错误：未选择任何视频文件！
    pause >nul
    goto file_select
)
goto start_encode

:check_duplicate
if exist "!output_file!" (
    set /a jk+=1
    set "output_file=%output_folder%!filename!~!jk!!ext!"
    goto check_duplicate
)
goto :eof

:start_encode
cls
echo ===================== 开始压制 =====================
if !subtitle_flag! equ 1 (
    echo 压制模式：内嵌字幕压制
) else (
    echo 压制模式：普通压制视频
)
echo 编码器：%encoder%
echo CRF值：%crf%
echo Preset：%preset%
if defined scale_param (
    echo 分辨率：720P
) else (
    echo 分辨率：原分辨率
)
echo 输出目录：%output_folder%
echo ============================================================
echo 按任意键继续
pause >nul

for %%f in (%input_files%) do (
    set "input_file=%%~f"
    set "filename=%%~nf"
    set "ext=.mp4"
    set "output_file=%output_folder%!filename!!ext!"
    set "jk=0"
    call :check_duplicate

    set "ffmpeg_cmd=ffmpeg -i "!input_file!" -c:v !encoder! -crf !crf! -preset !preset! -pix_fmt yuv420p10le"
    
    set "vf_filter="
    if defined scale_param set "vf_filter=!scale_param!"
    if !subtitle_flag!==1 (
        set "font_dir_esc=Fonts"
        set "sub_path_esc=!full_subtitle_path!"
        if defined vf_filter (
            set "vf_filter=!vf_filter!,subtitles='!sub_path_esc!':fontsdir='!font_dir_esc!'"
        ) else (
            set "vf_filter=subtitles='!sub_path_esc!':fontsdir='!font_dir_esc!'"
        )
    )
    if defined vf_filter set "ffmpeg_cmd=!ffmpeg_cmd! -vf "!vf_filter!""
    
    set "ffmpeg_cmd=!ffmpeg_cmd! -map 0:v:0 -map 0:a:0 -c:a copy -y "!output_file!""

    echo 正在压制：!input_file!
    echo 执行命令：!ffmpeg_cmd!
    !ffmpeg_cmd!

    echo 压制完成：!output_file!
    echo ============================================================
)

echo 所有文件压制完成！
echo 输出目录：%output_folder%
pause >nul
endlocal
exit /b