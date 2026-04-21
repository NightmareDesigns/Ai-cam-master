#ifndef STREAMDECODER_H
#define STREAMDECODER_H

#include <QObject>
#include <QImage>
#include <QByteArray>

class StreamDecoder : public QObject
{
    Q_OBJECT

public:
    explicit StreamDecoder(QObject *parent = nullptr);

    static QImage decodeFrame(const QByteArray &data);
    static bool isValidJpeg(const QByteArray &data);

private:
    static QImage decodeMJPEG(const QByteArray &data);
};

#endif // STREAMDECODER_H
