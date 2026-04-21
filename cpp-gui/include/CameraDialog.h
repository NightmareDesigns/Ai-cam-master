#ifndef CAMERADIALOG_H
#define CAMERADIALOG_H

#include <QDialog>
#include <QJsonObject>

QT_BEGIN_NAMESPACE
namespace Ui { class CameraDialog; }
QT_END_NAMESPACE

class CameraDialog : public QDialog
{
    Q_OBJECT

public:
    explicit CameraDialog(QWidget *parent = nullptr);
    ~CameraDialog();

    QJsonObject getCameraData() const;
    void setCameraData(const QJsonObject &data);

private:
    Ui::CameraDialog *ui;
};

#endif // CAMERADIALOG_H
