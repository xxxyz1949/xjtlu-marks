#pragma once

#include <QObject>
#include <QMutex>
#include <QThread>
#include <QAtomicInteger>
#include <QString>
#include <cstdarg>
#include <memory>
#include <mutex>

extern "C" {
#include <libavutil/pixfmt.h>
}

class D3D11Renderer;
struct AVFormatContext;
struct AVCodecContext;
struct AVStream;
struct AVPacket;
struct AVRational;
struct SwsContext;

class VideoPlayer : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool playing READ playing NOTIFY playingChanged)
    Q_PROPERTY(qint64 position READ position NOTIFY positionChanged)
    Q_PROPERTY(qint64 duration READ duration NOTIFY durationChanged)
    Q_PROPERTY(double volume READ volume WRITE setVolume NOTIFY volumeChanged)
    Q_PROPERTY(double playbackRate READ playbackRate WRITE setPlaybackRate NOTIFY playbackRateChanged)

public:
    explicit VideoPlayer(QObject *parent = nullptr);
    ~VideoPlayer();

    Q_INVOKABLE bool openFile(const QString &path);
    Q_INVOKABLE void play();
    Q_INVOKABLE void pause();
    Q_INVOKABLE void seek(qint64 ms);
    Q_INVOKABLE void setQualityParams(float brightness, float contrast, float saturation, float sharpness, float gamma);

    bool playing() const { return m_playing; }
    qint64 position() const { return m_position; }
    qint64 duration() const { return m_duration; }
    double volume() const { return m_volume; }
    double playbackRate() const { return m_playbackRate; }

public slots:
    void setVolume(double v);
    void setPlaybackRate(double r);

signals:
    void playingChanged();
    void positionChanged();
    void durationChanged();
    void volumeChanged();
    void playbackRateChanged();
    void statsUpdated(double fps, double dropRate);
    void qualityParamsChanged(float brightness, float contrast, float saturation, float sharpness, float gamma);

private:
    void stopInternal();
    static void initFFmpeg();
    static void ffmpegLogCallback(void *avcl, int level, const char *fmt, va_list vl);
    void closeInput();
    bool findStreams();
    bool openCodecs();
    bool createVideoDecoder(AVStream *stream);
    bool createAudioDecoder(AVStream *stream);
    bool configureVideoSwScale(int width, int height, AVPixelFormat pixFmt);

    bool m_playing{false};
    qint64 m_position{0};
    qint64 m_duration{0};
    double m_volume{1.0};
    double m_playbackRate{1.0};
    std::shared_ptr<D3D11Renderer> m_renderer;

    AVFormatContext *m_formatCtx{nullptr};
    AVCodecContext *m_videoCodecCtx{nullptr};
    AVCodecContext *m_audioCodecCtx{nullptr};
    SwsContext *m_swsCtx{nullptr};
    int m_videoStream{-1};
    int m_audioStream{-1};
    AVPixelFormat m_videoPixFmt{AV_PIX_FMT_NONE};
    int m_videoWidth{0};
    int m_videoHeight{0};
    QString m_currentPath;
    QString m_lastError;

    static std::once_flag s_ffmpegInitFlag;
};
