#ifndef SETTINGSDIALOG_H
#define SETTINGSDIALOG_H

#include <QDialog>

QT_BEGIN_NAMESPACE
namespace Ui { class SettingsDialog; }
QT_END_NAMESPACE

class SettingsDialog : public QDialog
{
    Q_OBJECT

public:
    explicit SettingsDialog(QWidget *parent = nullptr);
    ~SettingsDialog();

private slots:
    void onSaveClicked();
    void onCancelClicked();

private:
    void loadSettings();
    void saveSettings();

    Ui::SettingsDialog *ui;
};

#endif // SETTINGSDIALOG_H
