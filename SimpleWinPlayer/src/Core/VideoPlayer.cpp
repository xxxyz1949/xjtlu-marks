#include "VideoPlayer.h"
#include "Render/D3D11Renderer.h"
#include <QDebug>
#include <QProcessEnvironment>
#include <algorithm>
#include <array>
#include <cstdio>
#include <mutex>
#include <condition_variable>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>
#include <libavutil/hwcontext.h>
#include <libavutil/hwcontext_d3d11va.h>
#include <libavutil/pixdesc.h>
#include <libswscale/swscale.h>
}

std::once_flag VideoPlayer::s_ffmpegInitFlag;

VideoPlayer::VideoPlayer(QObject *parent) : QObject(parent) {
    initFFmpeg();
    m_renderer = std::make_shared<D3D11Renderer>();
}

VideoPlayer::~VideoPlayer() {
    stopInternal();
    closeInput();
}

bool VideoPlayer::openFile(const QString &path) {
    stopInternal();
    closeInput();

    m_currentPath = path;
    m_videoStream = -1;
    m_audioStream = -1;
    m_duration = 0;
    m_lastError.clear();
    m_videoWidth = 0;
    m_videoHeight = 0;
    m_videoPixFmt = AV_PIX_FMT_NONE;
    m_forceSwDecode = QProcessEnvironment::systemEnvironment().contains(QStringLiteral("SIMPLEWINPLAYER_FORCE_SW"));
    m_stopFlag = false;

    const QByteArray utf8Path = path.toUtf8();
    AVFormatContext *ctx = nullptr;
    int ret = avformat_open_input(&ctx, utf8Path.constData(), nullptr, nullptr);
    if (ret < 0) {
        m_lastError = QStringLiteral("打开文件失败: %1").arg(QString::fromUtf8(av_err2str(ret)));
        qWarning().noquote() << m_lastError;
        return false;
    }

    ret = avformat_find_stream_info(ctx, nullptr);
    if (ret < 0) {
        m_lastError = QStringLiteral("读取流信息失败: %1").arg(QString::fromUtf8(av_err2str(ret)));
        qWarning().noquote() << m_lastError;
        avformat_close_input(&ctx);
        return false;
    }

    m_formatCtx = ctx;

    if (!findStreams()) {
        avformat_close_input(&m_formatCtx);
        return false;
    }

    if (!openCodecs()) {
        closeInput();
        return false;
    }

    if (m_formatCtx->duration > 0) {
        m_duration = m_formatCtx->duration / (AV_TIME_BASE / 1000);
    } else {
        m_duration = 0;
    }
    emit durationChanged();

    qInfo().noquote() << "打开文件成功" << path
                      << "video_stream" << m_videoStream
                      << "audio_stream" << m_audioStream
                      << "时长(ms)" << m_duration;

    return true;
}

void VideoPlayer::play() {
    if (m_playing)
        return;
    m_playing = true;
    emit playingChanged();
    startDecodeThread();
}

void VideoPlayer::pause() {
    if (!m_playing)
        return;
    m_playing = false;
    emit playingChanged();
    stopDecodeThread();
}

void VideoPlayer::seek(qint64 ms) {
    m_position = ms;
    emit positionChanged();
    // TODO: perform FFmpeg seek
}

void VideoPlayer::setQualityParams(float brightness, float contrast, float saturation, float sharpness, float gamma) {
    if (m_renderer) {
        m_renderer->updateQuality(brightness, contrast, saturation, sharpness, gamma);
        emit qualityParamsChanged(brightness, contrast, saturation, sharpness, gamma);
    }
}

void VideoPlayer::setVolume(double v) {
    m_volume = v;
    emit volumeChanged();
    // TODO: apply volume to audio path
}

void VideoPlayer::setPlaybackRate(double r) {
    m_playbackRate = r;
    emit playbackRateChanged();
    // TODO: apply rate to audio/video clocks
}

void VideoPlayer::stopInternal() {
    m_playing = false;
    stopDecodeThread();
    clearFrames();
}

void VideoPlayer::closeInput() {
    if (m_formatCtx) {
        avformat_close_input(&m_formatCtx);
    }
    if (m_videoCodecCtx) {
        avcodec_free_context(&m_videoCodecCtx);
    }
    if (m_audioCodecCtx) {
        avcodec_free_context(&m_audioCodecCtx);
    }
    if (m_swsCtx) {
        sws_freeContext(m_swsCtx);
        m_swsCtx = nullptr;
    }
    if (m_hwDeviceCtx) {
        av_buffer_unref(&m_hwDeviceCtx);
    }
}

bool VideoPlayer::findStreams() {
    if (!m_formatCtx) {
        return false;
    }

    const int v = av_find_best_stream(m_formatCtx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    if (v >= 0) {
        m_videoStream = v;
    }

    const int a = av_find_best_stream(m_formatCtx, AVMEDIA_TYPE_AUDIO, -1, m_videoStream, nullptr, 0);
    if (a >= 0) {
        m_audioStream = a;
    }

    if (m_videoStream < 0 && m_audioStream < 0) {
        m_lastError = QStringLiteral("未找到可用的音/视频流");
        qWarning().noquote() << m_lastError;
        return false;
    }
    return true;
}

bool VideoPlayer::openCodecs() {
    if (m_videoStream < 0 && m_audioStream < 0) {
        return false;
    }

    if (m_videoStream >= 0) {
        AVStream *vs = m_formatCtx->streams[m_videoStream];
        if (!createVideoDecoder(vs)) {
            return false;
        }
        m_videoWidth = m_videoCodecCtx->width;
        m_videoHeight = m_videoCodecCtx->height;
        m_videoPixFmt = m_videoCodecCtx->pix_fmt;
    }

    if (m_audioStream >= 0) {
        AVStream *as = m_formatCtx->streams[m_audioStream];
        if (!createAudioDecoder(as)) {
            // 允许无音频，若音频打开失败则回退为仅视频
            qWarning().noquote() << "音频解码器创建失败，回退为仅视频";
            avcodec_free_context(&m_audioCodecCtx);
            m_audioStream = -1;
        }
    }
    return true;
}

bool VideoPlayer::createVideoDecoder(AVStream *stream) {
    const AVCodecParameters *par = stream->codecpar;
    const AVCodec *codec = avcodec_find_decoder(par->codec_id);
    if (!codec) {
        m_lastError = QStringLiteral("未找到视频解码器");
        qWarning().noquote() << m_lastError;
        return false;
    }
    auto allocAndConfig = [&](bool attachHw) -> bool {
        m_videoCodecCtx = avcodec_alloc_context3(codec);
        if (!m_videoCodecCtx) {
            m_lastError = QStringLiteral("分配视频解码上下文失败");
            qWarning().noquote() << m_lastError;
            return false;
        }
        if (avcodec_parameters_to_context(m_videoCodecCtx, par) < 0) {
            m_lastError = QStringLiteral("拷贝视频参数失败");
            qWarning().noquote() << m_lastError;
            return false;
        }

        m_videoCodecCtx->thread_count = std::max(2, QThread::idealThreadCount());
        m_videoCodecCtx->thread_type = FF_THREAD_SLICE | FF_THREAD_FRAME;

        if (attachHw && m_hwDeviceCtx) {
            m_videoCodecCtx->hw_device_ctx = av_buffer_ref(m_hwDeviceCtx);
            m_videoCodecCtx->get_format = &VideoPlayer::getHwFormat;
            m_videoCodecCtx->opaque = this;
        }

        if (avcodec_open2(m_videoCodecCtx, codec, nullptr) < 0) {
            return false;
        }
        return true;
    };

    bool useHw = !m_forceSwDecode;
    if (useHw && !createHwDevice()) {
        useHw = false;
    }

    if (useHw && allocAndConfig(true)) {
        // HW 成功
    } else {
        if (m_videoCodecCtx) {
            avcodec_free_context(&m_videoCodecCtx);
        }
        if (!allocAndConfig(false)) {
            m_lastError = QStringLiteral("打开视频解码器失败");
            qWarning().noquote() << m_lastError;
            return false;
        }
    }

    // 软解路径的色彩转换上下文（后续可替换为 D3D11 零拷）
    configureVideoSwScale(m_videoCodecCtx->width, m_videoCodecCtx->height, m_videoCodecCtx->pix_fmt);
    return true;
}

bool VideoPlayer::createAudioDecoder(AVStream *stream) {
    const AVCodecParameters *par = stream->codecpar;
    const AVCodec *codec = avcodec_find_decoder(par->codec_id);
    if (!codec) {
        qWarning().noquote() << "未找到音频解码器";
        return false;
    }
    m_audioCodecCtx = avcodec_alloc_context3(codec);
    if (!m_audioCodecCtx) {
        qWarning().noquote() << "分配音频解码上下文失败";
        return false;
    }
    if (avcodec_parameters_to_context(m_audioCodecCtx, par) < 0) {
        qWarning().noquote() << "拷贝音频参数失败";
        return false;
    }
    if (avcodec_open2(m_audioCodecCtx, codec, nullptr) < 0) {
        qWarning().noquote() << "打开音频解码器失败";
        return false;
    }
    return true;
}

void VideoPlayer::startDecodeThread() {
    if (!m_formatCtx || !m_videoCodecCtx) {
        qWarning().noquote() << "尚未打开视频解码器，无法启动解码线程";
        return;
    }
    if (m_decodeThread.joinable()) {
        return;
    }
    m_stopFlag = false;
    m_decodeThread = std::thread(&VideoPlayer::decodeLoop, this);
}

void VideoPlayer::stopDecodeThread() {
    m_stopFlag = true;
    m_queueCv.notify_all();
    if (m_decodeThread.joinable()) {
        m_decodeThread.join();
    }
}

void VideoPlayer::clearFrames() {
    std::lock_guard<std::mutex> lock(m_queueMutex);
    for (auto &f : m_frameQueue) {
        av_frame_free(&f.frame);
    }
    m_frameQueue.clear();
}

int64_t VideoPlayer::toMs(int64_t pts, AVRational timeBase) const {
    if (pts == AV_NOPTS_VALUE) return 0;
    return static_cast<int64_t>(pts * av_q2d(timeBase) * 1000.0);
}

void VideoPlayer::decodeLoop() {
    AVPacket *pkt = av_packet_alloc();
    AVFrame *frame = av_frame_alloc();
    const AVRational tb = m_formatCtx->streams[m_videoStream]->time_base;

    while (!m_stopFlag) {
        {
            std::unique_lock<std::mutex> lock(m_queueMutex);
            m_queueCv.wait(lock, [&] { return m_stopFlag || m_frameQueue.size() < kMaxFrames; });
            if (m_stopFlag) break;
        }

        int ret = av_read_frame(m_formatCtx, pkt);
        if (ret == AVERROR_EOF) {
            avcodec_send_packet(m_videoCodecCtx, nullptr);
        } else if (ret < 0) {
            continue;
        }

        if (pkt->stream_index == m_videoStream || ret == AVERROR_EOF) {
            if (ret != AVERROR_EOF) {
                avcodec_send_packet(m_videoCodecCtx, pkt);
            }
            while (!m_stopFlag) {
                ret = avcodec_receive_frame(m_videoCodecCtx, frame);
                if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                    break;
                }
                if (ret < 0) {
                    break;
                }
                processFrame(frame, tb);
            }
        }

        av_packet_unref(pkt);
    }

    av_frame_free(&frame);
    av_packet_free(&pkt);
}

void VideoPlayer::processFrame(AVFrame *frame, const AVRational &tb) {
    const bool isHw = frame->format == AV_PIX_FMT_D3D11;
    const int64_t ptsMs = toMs(frame->best_effort_timestamp, tb);

    if (m_renderer) {
        if (isHw) {
            ID3D11Texture2D *hwTex = reinterpret_cast<ID3D11Texture2D*>(frame->data[0]);
            m_renderer->copyFromHwTexture(hwTex);
        } else {
            // 软解转 BGRA 上传
            int width = frame->width;
            int height = frame->height;
            m_swBgraStride = width * 4;
            m_swBgra.resize(static_cast<size_t>(m_swBgraStride * height));
            uint8_t *dstSlice[4] = { m_swBgra.data(), nullptr, nullptr, nullptr };
            int dstStride[4] = { m_swBgraStride, 0, 0, 0 };
            sws_scale(m_swsCtx,
                      frame->data,
                      frame->linesize,
                      0,
                      height,
                      dstSlice,
                      dstStride);
            m_renderer->uploadBGRA(m_swBgra.data(), m_swBgraStride, width, height);
        }

        m_renderer->render();
    }

    {
        std::lock_guard<std::mutex> lock(m_queueMutex);
        if (m_frameQueue.size() >= kMaxFrames) {
            av_frame_free(&m_frameQueue.front().frame);
            m_frameQueue.pop_front();
        }
        m_frameQueue.push_back({av_frame_clone(frame), ptsMs});
    }
    m_queueCv.notify_all();
    m_position = ptsMs;
    emit positionChanged();
}

bool VideoPlayer::configureVideoSwScale(int width, int height, AVPixelFormat pixFmt) {
    if (pixFmt == AV_PIX_FMT_D3D11) {
        return true; // 硬解路径使用 D3D11 纹理，不在 swscale 中转换
    }

    if (m_swsCtx) {
        sws_freeContext(m_swsCtx);
        m_swsCtx = nullptr;
    }

    m_swsCtx = sws_getContext(width, height, pixFmt,
                              width, height, AV_PIX_FMT_BGRA,
                              SWS_BILINEAR, nullptr, nullptr, nullptr);
    if (!m_swsCtx) {
        qWarning().noquote() << "创建 sws 上下文失败";
        return false;
    }
    return true;
}

bool VideoPlayer::createHwDevice() {
    if (m_hwDeviceCtx) {
        return true;
    }

    int ret = av_hwdevice_ctx_create(&m_hwDeviceCtx, AV_HWDEVICE_TYPE_D3D11VA, nullptr, nullptr, 0);
    if (ret < 0) {
        qWarning().noquote() << "创建 D3D11VA 硬件设备失败，回退软解:" << QString::fromUtf8(av_err2str(ret));
        return false;
    }
    return true;
}

enum AVPixelFormat VideoPlayer::getHwFormat(AVCodecContext *ctx, const enum AVPixelFormat *pix_fmts) {
    if (!ctx) return AV_PIX_FMT_NONE;
    auto *player = reinterpret_cast<VideoPlayer*>(ctx->opaque);
    Q_UNUSED(player);

    for (const enum AVPixelFormat *p = pix_fmts; *p != AV_PIX_FMT_NONE; ++p) {
        if (*p == AV_PIX_FMT_D3D11) {
            return *p;
        }
    }

    // 若未发现 D3D11，回退为首选软解格式
    return pix_fmts ? pix_fmts[0] : AV_PIX_FMT_NONE;
}

void VideoPlayer::initFFmpeg() {
    std::call_once(s_ffmpegInitFlag, [] {
        av_log_set_level(AV_LOG_WARNING);
        av_log_set_callback(&VideoPlayer::ffmpegLogCallback);
        avformat_network_init();
    });
}

void VideoPlayer::ffmpegLogCallback(void *avcl, int level, const char *fmt, va_list vl) {
    Q_UNUSED(avcl);
    if (level > av_log_get_level()) {
        return;
    }

    std::array<char, 1024> buffer{};
    const int written = vsnprintf(buffer.data(), buffer.size(), fmt, vl);
    if (written <= 0) {
        return;
    }

    // Trim trailing newline to keep Qt logs compact
    if (written > 0) {
        const size_t len = std::min<size_t>(static_cast<size_t>(written), buffer.size() - 1);
        if (len > 0 && buffer[len - 1] == '\n') {
            buffer[len - 1] = '\0';
        }
    }

    if (level <= AV_LOG_ERROR) {
        qCritical().noquote() << buffer.data();
    } else if (level <= AV_LOG_WARNING) {
        qWarning().noquote() << buffer.data();
    } else {
        qDebug().noquote() << buffer.data();
    }
}
