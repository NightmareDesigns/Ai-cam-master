#include "EventsTableWidget.h"
#include <QHeaderView>
#include <QJsonObject>
#include <QDateTime>

EventsTableWidget::EventsTableWidget(QWidget *parent)
    : QTableWidget(parent)
{
    setupHeaders();
}

void EventsTableWidget::setupHeaders()
{
    setColumnCount(5);
    setHorizontalHeaderLabels({"Time", "Camera", "Type", "Class", "Confidence"});

    horizontalHeader()->setStretchLastSection(true);
    horizontalHeader()->setSectionResizeMode(QHeaderView::ResizeToContents);

    setEditTriggers(QAbstractItemView::NoEditTriggers);
    setSelectionBehavior(QAbstractItemView::SelectRows);
    setSelectionMode(QAbstractItemView::SingleSelection);
    setAlternatingRowColors(true);
}

void EventsTableWidget::updateEvents(const QJsonArray &events)
{
    setRowCount(0);

    int row = 0;
    for (const QJsonValue &value : events) {
        QJsonObject event = value.toObject();

        insertRow(row);

        // Time
        QString timestamp = event["timestamp"].toString();
        QDateTime dateTime = QDateTime::fromString(timestamp, Qt::ISODate);
        setItem(row, 0, new QTableWidgetItem(dateTime.toString("MM/dd hh:mm:ss")));

        // Camera
        QString cameraName = event["camera_name"].toString();
        if (cameraName.isEmpty()) {
            cameraName = QString("Camera %1").arg(event["camera_id"].toInt());
        }
        setItem(row, 1, new QTableWidgetItem(cameraName));

        // Type
        QString eventType = event["event_type"].toString();
        setItem(row, 2, new QTableWidgetItem(eventType));

        // Class
        QString detectedClass = event["detected_class"].toString();
        setItem(row, 3, new QTableWidgetItem(detectedClass));

        // Confidence
        double confidence = event["confidence"].toDouble();
        QString confidenceStr = QString("%1%").arg(static_cast<int>(confidence * 100));
        setItem(row, 4, new QTableWidgetItem(confidenceStr));

        row++;
    }
}
