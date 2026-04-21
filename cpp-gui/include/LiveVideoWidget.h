#ifndef LIVEVIDEOWIDGET_H
#define LIVEVIDEOWIDGET_H

#include <QWidget>
#include <QLabel>
#include <QWebSocket>
#include <QPixmap>
#include <QTimer>

class LiveVideoWidget : public QWidget
{
    Q_OBJECT

public:
    explicit LiveVideoWidget(int cameraId, const QString &name, QWidget *parent = nullptr);
    ~LiveVideoWidget();

    void setStreamUrl(const QString &url);
    void startStream();
    void stopStream();
    int cameraId() const { return m_cameraId; }

signals:
    void clicked(int cameraId);

protected:
    void mousePressEvent(QMouseEvent *event) override;

private slots:
    void onWebSocketConnected();
    void onWebSocketDisconnected();
    void onBinaryMessageReceived(const QByteArray &message);
    void onWebSocketError(QAbstractSocket::SocketError error);
    void updateSnapshot();

private:
    void setupUi();
    void connectToWebSocket();

    int m_cameraId;
    QString m_name;
    QString m_streamUrl;
    QLabel *m_videoLabel;
    QLabel *m_nameLabel;
    QLabel *m_statusLabel;
    QWebSocket *m_webSocket;
    QTimer *m_snapshotTimer;
    QPixmap m_currentFrame;
    bool m_isConnected;
};

#endif // LIVEVIDEOWIDGET_H
