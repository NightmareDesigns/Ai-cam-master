#ifndef PYTHONBACKEND_H
#define PYTHONBACKEND_H

#include <QObject>
#include <QProcess>
#include <QString>

class PythonBackend : public QObject
{
    Q_OBJECT

public:
    explicit PythonBackend(QObject *parent = nullptr);
    ~PythonBackend();

    void start();
    void stop();
    bool isRunning() const;

signals:
    void started();
    void stopped();
    void error(const QString &message);
    void outputReceived(const QString &output);

private slots:
    void onProcessStarted();
    void onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void onProcessError(QProcess::ProcessError error);
    void onReadyReadStandardOutput();
    void onReadyReadStandardError();

private:
    QString findBackendExecutable();

    QProcess *m_process;
    bool m_isRunning;
};

#endif // PYTHONBACKEND_H
