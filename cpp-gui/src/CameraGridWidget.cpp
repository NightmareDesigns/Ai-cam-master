#include "CameraGridWidget.h"
#include "LiveVideoWidget.h"
#include <QJsonObject>
#include <cmath>

CameraGridWidget::CameraGridWidget(QWidget *parent)
    : QWidget(parent)
    , m_layout(new QGridLayout(this))
{
    setupLayout();
}

void CameraGridWidget::setupLayout()
{
    m_layout->setSpacing(10);
    m_layout->setContentsMargins(5, 5, 5, 5);
    setLayout(m_layout);
}

void CameraGridWidget::updateCameras(const QJsonArray &cameras)
{
    // Remove widgets for cameras that no longer exist
    QList<int> currentIds;
    for (const QJsonValue &value : cameras) {
        QJsonObject camera = value.toObject();
        currentIds.append(camera["id"].toInt());
    }

    QList<int> idsToRemove;
    for (int id : m_cameraWidgets.keys()) {
        if (!currentIds.contains(id)) {
            idsToRemove.append(id);
        }
    }

    for (int id : idsToRemove) {
        LiveVideoWidget *widget = m_cameraWidgets.take(id);
        widget->stopStream();
        m_layout->removeWidget(widget);
        widget->deleteLater();
    }

    // Add or update camera widgets
    for (const QJsonValue &value : cameras) {
        QJsonObject camera = value.toObject();
        int id = camera["id"].toInt();
        QString name = camera["name"].toString();

        if (!m_cameraWidgets.contains(id)) {
            LiveVideoWidget *widget = new LiveVideoWidget(id, name, this);
            m_cameraWidgets[id] = widget;

            connect(widget, &LiveVideoWidget::clicked, this, &CameraGridWidget::cameraClicked);

            widget->startStream();
        }
    }

    // Reorganize layout
    int columns = calculateColumns(m_cameraWidgets.size());
    int row = 0, col = 0;

    for (LiveVideoWidget *widget : m_cameraWidgets.values()) {
        m_layout->addWidget(widget, row, col);
        col++;
        if (col >= columns) {
            col = 0;
            row++;
        }
    }
}

void CameraGridWidget::clear()
{
    for (LiveVideoWidget *widget : m_cameraWidgets.values()) {
        widget->stopStream();
        widget->deleteLater();
    }
    m_cameraWidgets.clear();
}

int CameraGridWidget::calculateColumns(int count)
{
    if (count == 0) return 1;
    if (count == 1) return 1;
    if (count <= 4) return 2;
    if (count <= 9) return 3;
    return 4;
}
