#ifndef CAMERAGRIDWIDGET_H
#define CAMERAGRIDWIDGET_H

#include <QWidget>
#include <QGridLayout>
#include <QJsonArray>
#include <QMap>

class LiveVideoWidget;

class CameraGridWidget : public QWidget
{
    Q_OBJECT

public:
    explicit CameraGridWidget(QWidget *parent = nullptr);

    void updateCameras(const QJsonArray &cameras);
    void clear();

signals:
    void cameraClicked(int cameraId);

private:
    void setupLayout();
    int calculateColumns(int count);

    QGridLayout *m_layout;
    QMap<int, LiveVideoWidget*> m_cameraWidgets;
};

#endif // CAMERAGRIDWIDGET_H
