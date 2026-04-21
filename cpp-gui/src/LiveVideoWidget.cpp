#include "LiveVideoWidget.h"
#include "StreamDecoder.h"
#include <QVBoxLayout>
#include <QMouseEvent>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QNetworkAccessManager>

LiveVideoWidget::LiveVideoWidget(int cameraId, const QString &name, QWidget *parent)
    : QWidget(parent)
    , m_cameraId(cameraId)
    , m_name(name)
    , m_streamUrl(QString("ws://localhost:8000/ws/%1").arg(cameraId))
    , m_videoLabel(nullptr)
    , m_nameLabel(nullptr)
    , m_statusLabel(nullptr)
    , m_webSocket(nullptr)
    , m_snapshotTimer(nullptr)
    , m_isConnected(false)
{
    setupUi();
}

LiveVideoWidget::~LiveVideoWidget()
{
    stopStream();
}

void LiveVideoWidget::setupUi()
{
    setMinimumSize(320, 240);
    setMaximumSize(640, 480);

    QVBoxLayout *layout = new QVBoxLayout(this);
    layout->setContentsMargins(5, 5, 5, 5);

    // Video display
    m_videoLabel = new QLabel(this);
    m_videoLabel->setMinimumSize(300, 200);
    m_videoLabel->setScaledContents(true);
    m_videoLabel->setStyleSheet("QLabel { background-color: #1a1a1a; border: 2px solid #404040; }");
    m_videoLabel->setAlignment(Qt::AlignCenter);
    m_videoLabel->setText("Loading...");
    layout->addWidget(m_videoLabel);

    // Camera name
    m_nameLabel = new QLabel(m_name, this);
    m_nameLabel->setStyleSheet("font-weight: bold; padding: 5px;");
    layout->addWidget(m_nameLabel);

    // Status
    m_statusLabel = new QLabel("● Connecting...", this);
    m_statusLabel->setStyleSheet("color: #ffa500; padding: 2px;");
    layout->addWidget(m_statusLabel);

    setLayout(layout);

    // Snapshot timer as fallback
    m_snapshotTimer = new QTimer(this);
    m_snapshotTimer->setInterval(1000); // 1 FPS fallback
    connect(m_snapshotTimer, &QTimer::timeout, this, &LiveVideoWidget::updateSnapshot);
}

void LiveVideoWidget::setStreamUrl(const QString &url)
{
    m_streamUrl = url;
}

void LiveVideoWidget::startStream()
{
    connectToWebSocket();
    m_snapshotTimer->start();
}

void LiveVideoWidget::stopStream()
{
    if (m_webSocket) {
        m_webSocket->close();
        m_webSocket->deleteLater();
        m_webSocket = nullptr;
    }

    if (m_snapshotTimer) {
        m_snapshotTimer->stop();
    }

    m_isConnected = false;
}

void LiveVideoWidget::connectToWebSocket()
{
    if (m_webSocket) {
        m_webSocket->deleteLater();
    }

    m_webSocket = new QWebSocket(QString(), QWebSocketProtocol::VersionLatest, this);

    connect(m_webSocket, &QWebSocket::connected, this, &LiveVideoWidget::onWebSocketConnected);
    connect(m_webSocket, &QWebSocket::disconnected, this, &LiveVideoWidget::onWebSocketDisconnected);
    connect(m_webSocket, &QWebSocket::binaryMessageReceived, this, &LiveVideoWidget::onBinaryMessageReceived);
    connect(m_webSocket, QOverload<QAbstractSocket::SocketError>::of(&QWebSocket::errorOccurred),
            this, &LiveVideoWidget::onWebSocketError);

    m_webSocket->open(QUrl(m_streamUrl));
}

void LiveVideoWidget::onWebSocketConnected()
{
    m_isConnected = true;
    m_statusLabel->setText("● Live");
    m_statusLabel->setStyleSheet("color: #00ff00; padding: 2px;");
}

void LiveVideoWidget::onWebSocketDisconnected()
{
    m_isConnected = false;
    m_statusLabel->setText("● Disconnected");
    m_statusLabel->setStyleSheet("color: #ff0000; padding: 2px;");

    // Try to reconnect after 5 seconds
    QTimer::singleShot(5000, this, &LiveVideoWidget::connectToWebSocket);
}

void LiveVideoWidget::onBinaryMessageReceived(const QByteArray &message)
{
    QImage image = StreamDecoder::decodeFrame(message);

    if (!image.isNull()) {
        m_currentFrame = QPixmap::fromImage(image);
        m_videoLabel->setPixmap(m_currentFrame.scaled(m_videoLabel->size(),
                                                       Qt::KeepAspectRatio,
                                                       Qt::SmoothTransformation));
    }
}

void LiveVideoWidget::onWebSocketError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error);
    m_statusLabel->setText("● Error");
    m_statusLabel->setStyleSheet("color: #ff0000; padding: 2px;");
}

void LiveVideoWidget::updateSnapshot()
{
    // Fallback: fetch snapshot via HTTP
    if (!m_isConnected) {
        QNetworkAccessManager *manager = new QNetworkAccessManager(this);
        QNetworkRequest request(QUrl(QString("http://localhost:8000/snapshot/%1").arg(m_cameraId)));

        QNetworkReply *reply = manager->get(request);

        connect(reply, &QNetworkReply::finished, this, [this, reply, manager]() {
            reply->deleteLater();
            manager->deleteLater();

            if (reply->error() == QNetworkReply::NoError) {
                QByteArray data = reply->readAll();
                QImage image = StreamDecoder::decodeFrame(data);

                if (!image.isNull()) {
                    m_currentFrame = QPixmap::fromImage(image);
                    m_videoLabel->setPixmap(m_currentFrame.scaled(m_videoLabel->size(),
                                                                   Qt::KeepAspectRatio,
                                                                   Qt::SmoothTransformation));
                }
            }
        });
    }
}

void LiveVideoWidget::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        emit clicked(m_cameraId);
    }
    QWidget::mousePressEvent(event);
}
