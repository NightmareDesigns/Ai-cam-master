#ifndef APICLIENT_H
#define APICLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QJsonArray>
#include <QJsonObject>
#include <functional>

class ApiClient : public QObject
{
    Q_OBJECT

public:
    explicit ApiClient(const QString &baseUrl = "http://localhost:8000", QObject *parent = nullptr);

    void getCameras(std::function<void(const QJsonArray&)> callback);
    void getEvents(std::function<void(const QJsonArray&)> callback);
    void getStats(std::function<void(const QJsonObject&)> callback);
    void addCamera(const QJsonObject &camera, std::function<void(bool)> callback);
    void deleteCamera(int cameraId, std::function<void(bool)> callback);
    void triggerDiscovery(std::function<void(const QJsonArray&)> callback);

signals:
    void error(const QString &message);

private:
    void handleReply(QNetworkReply *reply, std::function<void(const QJsonDocument&)> callback);

    QNetworkAccessManager *m_networkManager;
    QString m_baseUrl;
};

#endif // APICLIENT_H
