#include "PythonBackend.h"
#include <QCoreApplication>
#include <QDir>
#include <QStandardPaths>
#include <QThread>

PythonBackend::PythonBackend(QObject *parent)
    : QObject(parent)
    , m_process(new QProcess(this))
    , m_isRunning(false)
{
    connect(m_process, &QProcess::started, this, &PythonBackend::onProcessStarted);
    connect(m_process, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &PythonBackend::onProcessFinished);
    connect(m_process, &QProcess::errorOccurred, this, &PythonBackend::onProcessError);
    connect(m_process, &QProcess::readyReadStandardOutput, this, &PythonBackend::onReadyReadStandardOutput);
    connect(m_process, &QProcess::readyReadStandardError, this, &PythonBackend::onReadyReadStandardError);
}

PythonBackend::~PythonBackend()
{
    stop();
}

void PythonBackend::start()
{
    if (m_isRunning) {
        return;
    }

    QString backendPath = findBackendExecutable();

    if (backendPath.isEmpty()) {
        emit error("Backend executable not found");
        return;
    }

    m_process->setProgram(backendPath);
    m_process->setWorkingDirectory(QCoreApplication::applicationDirPath());

    // Set environment variables
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("HOST", "127.0.0.1");
    env.insert("PORT", "8000");
    m_process->setProcessEnvironment(env);

    m_process->start();
}

void PythonBackend::stop()
{
    if (m_isRunning && m_process->state() != QProcess::NotRunning) {
        m_process->terminate();
        if (!m_process->waitForFinished(5000)) {
            m_process->kill();
        }
    }
    m_isRunning = false;
}

bool PythonBackend::isRunning() const
{
    return m_isRunning;
}

void PythonBackend::onProcessStarted()
{
    m_isRunning = true;

    // Wait a bit for the server to fully start
    QThread::sleep(3);

    emit started();
}

void PythonBackend::onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    m_isRunning = false;

    if (exitStatus == QProcess::CrashExit) {
        emit error(QString("Backend crashed with exit code %1").arg(exitCode));
    }

    emit stopped();
}

void PythonBackend::onProcessError(QProcess::ProcessError error)
{
    QString errorMsg;

    switch (error) {
    case QProcess::FailedToStart:
        errorMsg = "Failed to start backend process";
        break;
    case QProcess::Crashed:
        errorMsg = "Backend process crashed";
        break;
    case QProcess::Timedout:
        errorMsg = "Backend process timed out";
        break;
    case QProcess::WriteError:
        errorMsg = "Write error to backend process";
        break;
    case QProcess::ReadError:
        errorMsg = "Read error from backend process";
        break;
    default:
        errorMsg = "Unknown error with backend process";
        break;
    }

    emit this->error(errorMsg);
}

void PythonBackend::onReadyReadStandardOutput()
{
    QString output = QString::fromUtf8(m_process->readAllStandardOutput());
    emit outputReceived(output);
}

void PythonBackend::onReadyReadStandardError()
{
    QString output = QString::fromUtf8(m_process->readAllStandardError());
    emit outputReceived(output);
}

QString PythonBackend::findBackendExecutable()
{
    QString appDir = QCoreApplication::applicationDirPath();

    // List of possible backend locations
    QStringList possiblePaths = {
#ifdef Q_OS_WIN
        appDir + "/aicam-backend.exe",
        appDir + "/../aicam-backend.exe",
        appDir + "/backend/aicam-backend.exe",
#elif defined(Q_OS_MAC)
        appDir + "/backend/aicam-backend",
        appDir + "/../Resources/aicam-backend",
        appDir + "/aicam-backend",
#else
        appDir + "/aicam-backend",
        appDir + "/../bin/aicam-backend",
        appDir + "/backend/aicam-backend",
#endif
    };

    for (const QString &path : possiblePaths) {
        QFileInfo fileInfo(path);
        if (fileInfo.exists() && fileInfo.isFile()) {
            return fileInfo.absoluteFilePath();
        }
    }

    return QString();
}
