#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTimer>
#include <memory>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class CameraGridWidget;
class EventsTableWidget;
class ApiClient;
class PythonBackend;

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onAddCameraClicked();
    void onRefreshClicked();
    void onSettingsClicked();
    void onAutoDiscoverClicked();
    void onBackendStarted();
    void onBackendError(const QString &error);
    void updateCameraGrid();
    void updateEvents();
    void updateStats();

private:
    void setupUi();
    void connectSignals();
    void startBackend();

    Ui::MainWindow *ui;
    CameraGridWidget *m_cameraGrid;
    EventsTableWidget *m_eventsTable;
    std::unique_ptr<ApiClient> m_apiClient;
    std::unique_ptr<PythonBackend> m_pythonBackend;
    QTimer *m_refreshTimer;
};

#endif // MAINWINDOW_H
