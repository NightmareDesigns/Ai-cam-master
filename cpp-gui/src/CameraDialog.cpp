#include "CameraDialog.h"
#include <QVBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QComboBox>
#include <QCheckBox>
#include <QDialogButtonBox>
#include <QLabel>

CameraDialog::CameraDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("Add Camera");
    setMinimumWidth(500);

    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    QFormLayout *formLayout = new QFormLayout();

    QLineEdit *nameEdit = new QLineEdit(this);
    nameEdit->setObjectName("nameEdit");
    nameEdit->setPlaceholderText("e.g., Front Door");
    formLayout->addRow("Name:", nameEdit);

    QLineEdit *sourceEdit = new QLineEdit(this);
    sourceEdit->setObjectName("sourceEdit");
    sourceEdit->setPlaceholderText("rtsp://user:pass@192.168.1.100:554/stream1");
    formLayout->addRow("Source URL:", sourceEdit);

    QCheckBox *enabledCheck = new QCheckBox("Enabled", this);
    enabledCheck->setObjectName("enabledCheck");
    enabledCheck->setChecked(true);
    formLayout->addRow("Status:", enabledCheck);

    QCheckBox *aiDetectionCheck = new QCheckBox("Enable AI Detection", this);
    aiDetectionCheck->setObjectName("aiDetectionCheck");
    aiDetectionCheck->setChecked(true);
    formLayout->addRow("AI Detection:", aiDetectionCheck);

    QCheckBox *motionDetectionCheck = new QCheckBox("Enable Motion Detection", this);
    motionDetectionCheck->setObjectName("motionDetectionCheck");
    motionDetectionCheck->setChecked(false);
    formLayout->addRow("Motion Detection:", motionDetectionCheck);

    mainLayout->addLayout(formLayout);

    QDialogButtonBox *buttonBox = new QDialogButtonBox(
        QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
    connect(buttonBox, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);

    mainLayout->addWidget(buttonBox);

    setLayout(mainLayout);
}

CameraDialog::~CameraDialog()
{
}

QJsonObject CameraDialog::getCameraData() const
{
    QJsonObject data;

    QLineEdit *nameEdit = findChild<QLineEdit*>("nameEdit");
    QLineEdit *sourceEdit = findChild<QLineEdit*>("sourceEdit");
    QCheckBox *enabledCheck = findChild<QCheckBox*>("enabledCheck");
    QCheckBox *aiDetectionCheck = findChild<QCheckBox*>("aiDetectionCheck");
    QCheckBox *motionDetectionCheck = findChild<QCheckBox*>("motionDetectionCheck");

    if (nameEdit) data["name"] = nameEdit->text();
    if (sourceEdit) data["source"] = sourceEdit->text();
    if (enabledCheck) data["enabled"] = enabledCheck->isChecked();
    if (aiDetectionCheck) data["ai_detection_enabled"] = aiDetectionCheck->isChecked();
    if (motionDetectionCheck) data["motion_detection_enabled"] = motionDetectionCheck->isChecked();

    return data;
}

void CameraDialog::setCameraData(const QJsonObject &data)
{
    QLineEdit *nameEdit = findChild<QLineEdit*>("nameEdit");
    QLineEdit *sourceEdit = findChild<QLineEdit*>("sourceEdit");
    QCheckBox *enabledCheck = findChild<QCheckBox*>("enabledCheck");
    QCheckBox *aiDetectionCheck = findChild<QCheckBox*>("aiDetectionCheck");
    QCheckBox *motionDetectionCheck = findChild<QCheckBox*>("motionDetectionCheck");

    if (nameEdit && data.contains("name")) nameEdit->setText(data["name"].toString());
    if (sourceEdit && data.contains("source")) sourceEdit->setText(data["source"].toString());
    if (enabledCheck && data.contains("enabled")) enabledCheck->setChecked(data["enabled"].toBool());
    if (aiDetectionCheck && data.contains("ai_detection_enabled"))
        aiDetectionCheck->setChecked(data["ai_detection_enabled"].toBool());
    if (motionDetectionCheck && data.contains("motion_detection_enabled"))
        motionDetectionCheck->setChecked(data["motion_detection_enabled"].toBool());
}
