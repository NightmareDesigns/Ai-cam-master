#include "StreamDecoder.h"
#include <QBuffer>
#include <QImageReader>

StreamDecoder::StreamDecoder(QObject *parent)
    : QObject(parent)
{
}

QImage StreamDecoder::decodeFrame(const QByteArray &data)
{
    if (!isValidJpeg(data)) {
        return QImage();
    }

    QBuffer buffer;
    buffer.setData(data);
    buffer.open(QIODevice::ReadOnly);

    QImageReader reader(&buffer, "JPEG");
    return reader.read();
}

bool StreamDecoder::isValidJpeg(const QByteArray &data)
{
    if (data.size() < 2) {
        return false;
    }

    // Check JPEG magic bytes (0xFF 0xD8)
    return (static_cast<unsigned char>(data[0]) == 0xFF &&
            static_cast<unsigned char>(data[1]) == 0xD8);
}

QImage StreamDecoder::decodeMJPEG(const QByteArray &data)
{
    // MJPEG is just a series of JPEG frames
    return decodeFrame(data);
}
