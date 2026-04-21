#include "ApiClient.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrlQuery>

ApiClient::ApiClient(const QString &baseUrl, QObject *parent)
    : QObject(parent)
    , m_networkManager(new QNetworkAccessManager(this))
    , m_baseUrl(baseUrl)
{
}

void ApiClient::getCameras(std::function<void(const QJsonArray&)> callback)
{
    QNetworkRequest request(QUrl(m_baseUrl + "/api/cameras/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply *reply = m_networkManager->get(request);

    handleReply(reply, [callback](const QJsonDocument &doc) {
        callback(doc.array());
    });
}

void ApiClient::getEvents(std::function<void(const QJsonArray&)> callback)
{
    QUrl url(m_baseUrl + "/api/events/");
    QUrlQuery query;
    query.addQueryItem("limit", "50");
    url.setQuery(query);

    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply *reply = m_networkManager->get(request);

    handleReply(reply, [callback](const QJsonDocument &doc) {
        callback(doc.array());
    });
}

void ApiClient::getStats(std::function<void(const QJsonObject&)> callback)
{
    QNetworkRequest request(QUrl(m_baseUrl + "/api/cameras/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply *reply = m_networkManager->get(request);

    handleReply(reply, [callback](const QJsonDocument &doc) {
        QJsonObject stats;
        stats["total_cameras"] = doc.array().size();
        stats["total_events"] = 0; // Will be updated
        callback(stats);
    });
}

void ApiClient::addCamera(const QJsonObject &camera, std::function<void(bool)> callback)
{
    QNetworkRequest request(QUrl(m_baseUrl + "/api/cameras/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonDocument doc(camera);
    QNetworkReply *reply = m_networkManager->post(request, doc.toJson());

    handleReply(reply, [callback](const QJsonDocument &) {
        callback(true);
    });
}

void ApiClient::deleteCamera(int cameraId, std::function<void(bool)> callback)
{
    QNetworkRequest request(QUrl(m_baseUrl + QString("/api/cameras/%1").arg(cameraId)));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply *reply = m_networkManager->deleteResource(request);

    handleReply(reply, [callback](const QJsonDocument &) {
        callback(true);
    });
}

void ApiClient::triggerDiscovery(std::function<void(const QJsonArray&)> callback)
{
    QNetworkRequest request(QUrl(m_baseUrl + "/api/cameras/discover"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject params;
    params["auto_add"] = true;

    QJsonDocument doc(params);
    QNetworkReply *reply = m_networkManager->post(request, doc.toJson());

    handleReply(reply, [callback](const QJsonDocument &doc) {
        QJsonObject obj = doc.object();
        callback(obj["discovered"].toArray());
    });
}

void ApiClient::handleReply(QNetworkReply *reply, std::function<void(const QJsonDocument&)> callback)
{
    connect(reply, &QNetworkReply::finished, this, [this, reply, callback]() {
        reply->deleteLater();

        if (reply->error() != QNetworkReply::NoError) {
            emit error(QString("Network error: %1").arg(reply->errorString()));
            return;
        }

        QByteArray data = reply->readAll();
        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);

        if (parseError.error != QJsonParseError::NoError) {
            emit error(QString("JSON parse error: %1").arg(parseError.errorString()));
            return;
        }

        callback(doc);
    });
}
