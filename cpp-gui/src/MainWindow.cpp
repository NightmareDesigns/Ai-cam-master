#include "MainWindow.h"
#include "CameraGridWidget.h"
#include "EventsTableWidget.h"
#include "ApiClient.h"
#include "PythonBackend.h"
#include "CameraDialog.h"
#include "SettingsDialog.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#include <QLabel>
#include <QMenuBar>
#include <QToolBar>
#include <QStatusBar>
#include <QMessageBox>
#include <QSplitter>
#include <QGroupBox>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , m_cameraGrid(nullptr)
    , m_eventsTable(nullptr)
    , m_apiClient(nullptr)
    , m_pythonBackend(nullptr)
    , m_refreshTimer(nullptr)
{
    setupUi();
    connectSignals();
    startBackend();
}

MainWindow::~MainWindow()
{
    if (m_pythonBackend) {
        m_pythonBackend->stop();
    }
}

void MainWindow::setupUi()
{
    setWindowTitle("AI-Cam - AI-Powered Security Camera Monitoring");
    setMinimumSize(1200, 800);

    // Create central widget with main layout
    QWidget *centralWidget = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);

    // Create toolbar
    QToolBar *toolbar = addToolBar("Main Toolbar");
    toolbar->setMovable(false);

    QAction *addCameraAction = toolbar->addAction("➕ Add Camera");
    QAction *refreshAction = toolbar->addAction("🔄 Refresh");
    QAction *discoverAction = toolbar->addAction("🔍 Auto-Discover");
    toolbar->addSeparator();
    QAction *settingsAction = toolbar->addAction("⚙️ Settings");

    connect(addCameraAction, &QAction::triggered, this, &MainWindow::onAddCameraClicked);
    connect(refreshAction, &QAction::triggered, this, &MainWindow::onRefreshClicked);
    connect(discoverAction, &QAction::triggered, this, &MainWindow::onAutoDiscoverClicked);
    connect(settingsAction, &QAction::triggered, this, &MainWindow::onSettingsClicked);

    // Stats panel
    QHBoxLayout *statsLayout = new QHBoxLayout();
    QLabel *statsLabel = new QLabel("Dashboard", this);
    statsLabel->setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;");
    statsLayout->addWidget(statsLabel);
    statsLayout->addStretch();
    mainLayout->addLayout(statsLayout);

    // Create splitter for cameras and events
    QSplitter *splitter = new QSplitter(Qt::Vertical, this);

    // Camera grid
    QGroupBox *cameraGroup = new QGroupBox("Live Cameras", this);
    QVBoxLayout *cameraLayout = new QVBoxLayout(cameraGroup);
    m_cameraGrid = new CameraGridWidget(this);
    cameraLayout->addWidget(m_cameraGrid);
    splitter->addWidget(cameraGroup);

    // Events table
    QGroupBox *eventsGroup = new QGroupBox("Recent Events", this);
    QVBoxLayout *eventsLayout = new QVBoxLayout(eventsGroup);
    m_eventsTable = new EventsTableWidget(this);
    eventsLayout->addWidget(m_eventsTable);
    splitter->addWidget(eventsGroup);

    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 1);

    mainLayout->addWidget(splitter);
    setCentralWidget(centralWidget);

    // Status bar
    statusBar()->showMessage("Initializing...");

    // Setup refresh timer
    m_refreshTimer = new QTimer(this);
    m_refreshTimer->setInterval(5000); // Refresh every 5 seconds
    connect(m_refreshTimer, &QTimer::timeout, this, &MainWindow::updateCameraGrid);
    connect(m_refreshTimer, &QTimer::timeout, this, &MainWindow::updateEvents);
}

void MainWindow::connectSignals()
{
    // Camera grid signals
    connect(m_cameraGrid, &CameraGridWidget::cameraClicked, this, [this](int cameraId) {
        QMessageBox::information(this, "Camera", QString("Camera ID: %1 clicked").arg(cameraId));
    });
}

void MainWindow::startBackend()
{
    m_pythonBackend = std::make_unique<PythonBackend>(this);

    connect(m_pythonBackend.get(), &PythonBackend::started, this, &MainWindow::onBackendStarted);
    connect(m_pythonBackend.get(), &PythonBackend::error, this, &MainWindow::onBackendError);

    statusBar()->showMessage("Starting AI-Cam backend...");
    m_pythonBackend->start();
}

void MainWindow::onBackendStarted()
{
    statusBar()->showMessage("Backend started successfully");

    // Initialize API client
    m_apiClient = std::make_unique<ApiClient>("http://localhost:8000", this);

    connect(m_apiClient.get(), &ApiClient::error, this, [this](const QString &error) {
        QMessageBox::warning(this, "API Error", error);
    });

    // Start refresh timer
    m_refreshTimer->start();

    // Initial data load
    updateCameraGrid();
    updateEvents();
    updateStats();
}

void MainWindow::onBackendError(const QString &error)
{
    statusBar()->showMessage("Backend error: " + error);
    QMessageBox::critical(this, "Backend Error",
        "Failed to start AI-Cam backend:\n\n" + error +
        "\n\nMake sure the backend executable is in the correct location.");
}

void MainWindow::updateCameraGrid()
{
    if (!m_apiClient) return;

    m_apiClient->getCameras([this](const QJsonArray &cameras) {
        m_cameraGrid->updateCameras(cameras);
        statusBar()->showMessage(QString("Cameras: %1").arg(cameras.size()));
    });
}

void MainWindow::updateEvents()
{
    if (!m_apiClient) return;

    m_apiClient->getEvents([this](const QJsonArray &events) {
        m_eventsTable->updateEvents(events);
    });
}

void MainWindow::updateStats()
{
    if (!m_apiClient) return;

    m_apiClient->getStats([this](const QJsonObject &stats) {
        // Update stats display
        QString msg = QString("Cameras: %1 | Events: %2")
            .arg(stats["total_cameras"].toInt())
            .arg(stats["total_events"].toInt());
        statusBar()->showMessage(msg);
    });
}

void MainWindow::onAddCameraClicked()
{
    CameraDialog dialog(this);
    if (dialog.exec() == QDialog::Accepted) {
        QJsonObject cameraData = dialog.getCameraData();
        m_apiClient->addCamera(cameraData, [this](bool success) {
            if (success) {
                QMessageBox::information(this, "Success", "Camera added successfully");
                updateCameraGrid();
            } else {
                QMessageBox::warning(this, "Error", "Failed to add camera");
            }
        });
    }
}

void MainWindow::onRefreshClicked()
{
    updateCameraGrid();
    updateEvents();
    updateStats();
}

void MainWindow::onSettingsClicked()
{
    SettingsDialog dialog(this);
    dialog.exec();
}

void MainWindow::onAutoDiscoverClicked()
{
    if (!m_apiClient) return;

    statusBar()->showMessage("Running auto-discovery...");
    m_apiClient->triggerDiscovery([this](const QJsonArray &discovered) {
        QString msg = QString("Discovered %1 cameras").arg(discovered.size());
        statusBar()->showMessage(msg);
        QMessageBox::information(this, "Discovery Complete", msg);
        updateCameraGrid();
    });
}
