#ifndef EVENTSTABLEWIDGET_H
#define EVENTSTABLEWIDGET_H

#include <QTableWidget>
#include <QJsonArray>

class EventsTableWidget : public QTableWidget
{
    Q_OBJECT

public:
    explicit EventsTableWidget(QWidget *parent = nullptr);

    void updateEvents(const QJsonArray &events);

private:
    void setupHeaders();
};

#endif // EVENTSTABLEWIDGET_H
