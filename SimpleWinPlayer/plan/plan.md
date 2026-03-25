## 计划：SimpleWinPlayer 实施

概述：在 Windows 上用 FFmpeg 6.1 + D3D11 解码/渲染，Qt/QML 做 UI，Pixel Shader 做实时画质调节；架构分 Core（C++ 解码/渲染）、UI（QML 控件/面板）、D3D11 像素着色器；CMake+vcpkg 静态构建。

**步骤**
1. 构建配置：vcpkg 清单/基线，ffmpeg[avcodec,avformat,avutil,swresample,swscale] 静态，qtbase/qtdeclarative/qtquick/qtshadertools；CMake 设 x64-windows-static，链接 D3D11/DXGI。
2. 布局：Core/（VideoPlayer、D3D11Renderer、辅助结构），shaders/（PixelShader.hlsl），ui/（QML），必要资源；添加应用、着色器编译（fxc/dxc）、QML 嵌入目标。
3. VideoPlayer：FFmpeg 初始化/打开流/选轨；D3D11VA 硬解+软解回退；解码线程；播放/暂停/Seek/倍速/音量；硬解零拷上传，软解 staging；基础 SRT/VTT 解析与计时；输出 fps/drop/画质参数。
4. D3D11Renderer：设备/上下文/交换链，NV12/RGB 纹理与 SRV，画质常量缓冲，编译/加载 PixelShader，全屏 quad 渲染，参数可每帧更新，支持软解回退。
5. PixelShader.hlsl：NV12/RGB 采样，亮度/对比度/饱和度/锐度/伽马，简单 unsharp，钳制输出，常量缓冲与 C++ 对齐。
6. UI/QML：main.qml + PlayerView 桥接，Controls（打开/播停/Seek/音量/倍速），SettingsPanel（画质滑块+重置，默认右侧展开、醒目），调试叠加显示 fps/drop/hw/CPU/GPU/内存，信号槽/Q_PROPERTY/Q_INVOKABLE 连接。
7. 入口：main.cpp 注册类型，QGuiApplication+QQmlApplicationEngine，加载 QML，文件对话框，默认值。
8. 验证钩子：线程安全析构，硬解回退验证，启动 <300ms（懒加载/预编译 shader），4K 路径用 D3D11VA，帧掉计数。
9. 构建/运行指南：vcpkg 安装、cmake 配置/构建/运行；静态/打包提示；样本矩阵建议（1080p/4K，硬/软解，Seek，字幕，画质滑块）。

**关键文件**
- CMakeLists.txt — 顶层构建、vcpkg 工具链、Qt/QML、shader 编译、FFmpeg 链接
- main.cpp — Qt 启动、类型注册、加载 QML
- Core/VideoPlayer.h/.cpp — 解码、硬解/软解、播放控制、统计、字幕
- Render/D3D11Renderer.h/.cpp — 设备/交换链、纹理上传、着色器管线、参数缓冲
- shaders/PixelShader.hlsl — 画质调节着色器
- ui/main.qml — 根窗口
- ui/Controls.qml — 播放控制（打开/播停/进度/音量/倍速）
- ui/SettingsPanel.qml — 画质滑块+重置；调试叠加
- 其他 Core 辅助头（帧类型、字幕解析）按需补充

**验证流程（含样本矩阵）**
1) 构建/运行：cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake -DVCPKG_TARGET_TRIPLET=x64-windows-static -DCMAKE_BUILD_TYPE=Release；cmake --build build --config Release；运行 SimpleWinPlayer。
2) 样本矩阵：分辨率/帧率 480p@24/30、1080p@24/30/60、4K@24/30/60；编码 H.264/H.265/HEVC/AV1（若支持）；容器 mp4/mkv/webm；音频 AAC/Opus/无音轨；字幕 外挂 SRT/VTT（UTF-8、GBK 各一）+ 内嵌轨。
3) 冒烟：480p MP4（AAC）播/停/Seek/可听见。
4) 硬解/软解判定：4K H.264 确认 D3D11VA（日志 hwaccel=d3d11va 或叠加 hw=on）；env SIMPLEWINPLAYER_FORCE_SW=1 强制软解，日志 software decode，可播放；硬解失败需记录 fallback，UI 可提示回退。
5) 性能（120s，优先 4K@60 硬解）：FPS≥目标 95%，丢帧<0.1%，CPU 合理，GPU Decode/3D 合理。
6) 画质滑块：快扫亮/对/饱/锐/伽马，下一帧生效，无卡顿；重置有效；叠加参数变化。
7) 字幕：外挂 UTF-8/GBK + 内嵌各一，Seek 后同步。
8) Seek/循环：快进/快退/短循环，恢复快，无崩溃。
9) 音频控制：音量极值/静音，倍速 0.5x/1x/2x 同步。
10) 窗口缩放：多次 resize，比例正确，交换链无错，叠加定位准。
11) 启动：冷启动到首帧 <300ms。
12) 稳定性：损坏/不支持文件提示不中断；快速切文件无崩溃。
13) 回归泄漏：多次开关文件内存不持续升。

**完成后立刻验证（Build-test pairing）**
- VideoPlayer 播放控制 → 冒烟+硬/软判定+坏文件
- 硬/软回退 → 4K 硬解 + 强制软解（日志/叠加 hw）
- Renderer+PixelShader → 滑块即时+120s 性能（FPS≥95%、丢帧<0.1%）
- 字幕 → 外挂/内嵌/UTF-8/GBK，同步且 Seek 后仍准
- UI/调试叠加 → fps/drop/hw/CPU/GPU/内存 1s 采样可开关
- 窗口缩放 → 反复 resize 正常
- 启动优化 → 冷启动<300ms
- 稳定性 → 快切/长播 10 分钟无泄漏

**指标与通过标准**
- FPS ≥ 目标帧率 95%；
- 丢帧率 <0.1%（120s，优先 4K@60）；
- 冷启动 <300ms；
- Seek：首帧 <250ms，A/V 恢复 <500ms；
- 滑块：<1 帧周期生效，Reset 同步；
- A/V 漂移 <80ms；字幕偏差 <50ms；
- CPU：4K@60 硬解总 CPU <50%（4C/8T 参考）；
- GPU：Decode <70%，3D <50%；
- 内存：10 分钟或多次开关波动 <5%，无句柄增长；
- 错误：损坏/不支持文件提示不中断，快切不崩溃。

**Micro tasks（子步骤 + 测试/整改）**
1) FFmpeg init&日志：av_log_set_level/注册解码器/日志回调；空启动不崩；整改降日志。
2) 打开/探测：Qt 对话框 + avformat_open_input/find_stream_info；合法显示时长，坏文件弹错不中断；整改分类提示。
3) 硬解 ctx+回退：D3D11 设备/av_hwdevice_ctx_create；失败切 sw；4K hw=on，env 强制 sw；整改补 fallback。
4) 解码循环+队列：独立线程，音视频队列，播放状态机；480p 播/停/Seek/倍速；整改限队列查锁。
5) 帧上传：hw 映射 Texture2D；sw NV12 staging→GPU；SRV；硬/软帧均显示；整改减 swscale/拷贝。
6) Renderer 基础：swapchain/RTV/sampler/quad；反复 resize 不黑屏；整改检查 flag/present。
7) PixelShader：常量缓冲+PS 编译，5 参数+Reset；滑块即时；整改降锐度 tap/权重。
8) 调试叠加：计时器采样 fps/drop/hw/CPU/GPU/内存；QML 显示可开关；整改调频率/格式。
9) 音频/音量/倍速：输出初始化、音量缩放、重采样倍速；0.5x/1x/2x 同步；整改查重采样缓冲。
10) Seek：av_seek_frame，清空旧帧，重置时钟，裁剪音频缓冲，控预填充；首帧<250ms，A/V<500ms；整改调队列/预填充。
11) 字幕：外挂 SRT/VTT UTF-8→GBK，内嵌轨；时钟对齐，QML 绘制；Seek 后同步，无乱码；整改编码开关、重建 cue。
12) 控制条：播/停/进度/音量/倍速信号槽；冒烟顺畅；整改节流去抖。
13) 画质面板：右侧展开、强调色、数值读数、Reset、小胶囊；即时反映；整改调布局配色。
14) 窗口缩放：处理 resize 重建 swapchain/视口，更新叠加；多次 resize 比例正确；整改顺序。
15) 启动优化：懒加载非核心，预编译核心 PS，减日志；冷启动<300ms；整改再推迟模块。
16) 性能 120s：记录 fps/drop/CPU/GPU/内存；FPS≥95% 丢帧<0.1%；整改按性能条目。
17) 稳定性：损坏/不支持、快切、多格式、长播 10 分钟；无崩溃无泄漏；整改释放资源、错处理。
18) 回归包：多次开关文件；内存/句柄无增长；整改加清理钩子。

**未达标整改动作**
- FPS/丢帧：查 hw=on；减拷贝/NV12 零拷；关/降锐度 tap；调队列/锁等待；必要时调 present/vsync。
- 启动：延迟字幕/对话框/非首帧 shader；预编译核心 PS；降启动日志 I/O。
- Seek/A/V：Seek 后丢弃旧帧、重置时钟、裁剪音频、缩短预填充；调队列；必要时静音填充；控重采样缓冲。
- 字幕：UTF-8→GBK fallback，可手动指定；Seek 后重建 cue；提高对比度/描边。
- CPU/GPU：关/降锐度核；确保硬解；软解可降分辨率或限线程；排查双拷贝/双转换/过高滤波。
- 内存/句柄：切文件释放解码器/纹理/SRV/字幕缓存，清空队列；定期采样资源，必要时抓堆；队列定长/显式清空。
- 错误处理：坏/不支持文件提示不中止；日志区分硬解创建失败/解码/I-O 错误，可自动切软解或中止。

**提交/推送流程（Tower + GitHub）**
- 原则：每完成一个元任务并通过对应测试后立即提交并 push；若为测试修复同样提交并 push；提交保持原子、可运行。
- 具体步骤：
	1) 保存：Ctrl+S 全部文件。
	2) 暂存：源代码控制面板逐个点击 +，或在根目录执行 `git add .`（或精确文件）。
	3) 提交：提交消息格式固定为 `feat: 完成[元任务名称]`（测试修复可用 `fix:`/`test:` 但仍建议写清元任务名）；确保描述已测场景。
	4) 推送：点击「同步更改」或执行 `git push origin master`（或当前分支）。
- 若远端提示仓库重定向，执行一次 `git remote set-url origin https://github.com/xxxyz1949/SimpleWinPlayer.git` 后继续使用 origin。
- 单次提交保持可运行且已验证；未达标先修复再提交。

**决策**
- 仅 Windows，vcpkg x64-windows-static 静态链接
- 硬解优先 D3D11VA，失败回退软解
- 不做流媒体/播放列表/HDR/皮肤/插件；只做本地文件与单字幕
- 仅信号槽；QML UI 覆盖 D3D11 渲染视频面

**其他**
1. 打包：优先静态；若用动态 Qt，windeployqt 并捆绑 FFmpeg DLL。
2. 着色器编译：默认 fxc（Win10 基线），若需 DXIL 可改 dxc。
