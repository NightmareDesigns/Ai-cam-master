#include "SettingsDialog.h"
#include <QVBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QSpinBox>
#include <QCheckBox>
#include <QDialogButtonBox>
#include <QSettings>
#include <QLabel>
#include <QGroupBox>

SettingsDialog::SettingsDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("Settings");
    setMinimumWidth(600);

    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    // General settings
    QGroupBox *generalGroup = new QGroupBox("General", this);
    QFormLayout *generalLayout = new QFormLayout(generalGroup);

    QLineEdit *hostEdit = new QLineEdit(this);
    hostEdit->setObjectName("hostEdit");
    hostEdit->setText("127.0.0.1");
    generalLayout->addRow("Backend Host:", hostEdit);

    QSpinBox *portSpin = new QSpinBox(this);
    portSpin->setObjectName("portSpin");
    portSpin->setRange(1, 65535);
    portSpin->setValue(8000);
    generalLayout->addRow("Backend Port:", portSpin);

    mainLayout->addWidget(generalGroup);

    // AI Detection settings
    QGroupBox *aiGroup = new QGroupBox("AI Detection", this);
    QFormLayout *aiLayout = new QFormLayout(aiGroup);

    QLineEdit *modelEdit = new QLineEdit(this);
    modelEdit->setObjectName("modelEdit");
    modelEdit->setText("yolov8n.pt");
    aiLayout->addRow("YOLO Model:", modelEdit);

    QSpinBox *confidenceSpin = new QSpinBox(this);
    confidenceSpin->setObjectName("confidenceSpin");
    confidenceSpin->setRange(1, 100);
    confidenceSpin->setValue(45);
    confidenceSpin->setSuffix("%");
    aiLayout->addRow("Confidence Threshold:", confidenceSpin);

    mainLayout->addWidget(aiGroup);

    // Auto-discovery settings
    QGroupBox *discoveryGroup = new QGroupBox("Auto-Discovery", this);
    QFormLayout *discoveryLayout = new QFormLayout(discoveryGroup);

    QCheckBox *autoDiscoveryCheck = new QCheckBox("Enable Auto-Discovery", this);
    autoDiscoveryCheck->setObjectName("autoDiscoveryCheck");
    autoDiscoveryCheck->setChecked(true);
    discoveryLayout->addRow(autoDiscoveryCheck);

    QCheckBox *brutForceCheck = new QCheckBox("Enable Credential Brute-Force", this);
    brutForceCheck->setObjectName("bruteForceCheck");
    brutForceCheck->setChecked(true);
    discoveryLayout->addRow(brutForceCheck);

    mainLayout->addWidget(discoveryGroup);

    // Buttons
    QDialogButtonBox *buttonBox = new QDialogButtonBox(
        QDialogButtonBox::Save | QDialogButtonBox::Cancel, this);
    connect(buttonBox, &QDialogButtonBox::accepted, this, &SettingsDialog::onSaveClicked);
    connect(buttonBox, &QDialogButtonBox::rejected, this, &SettingsDialog::onCancelClicked);

    mainLayout->addWidget(buttonBox);

    setLayout(mainLayout);

    loadSettings();
}

SettingsDialog::~SettingsDialog()
{
}

void SettingsDialog::loadSettings()
{
    QSettings settings("AI-Cam", "GUI");

    QLineEdit *hostEdit = findChild<QLineEdit*>("hostEdit");
    if (hostEdit) {
        hostEdit->setText(settings.value("host", "127.0.0.1").toString());
    }

    QSpinBox *portSpin = findChild<QSpinBox*>("portSpin");
    if (portSpin) {
        portSpin->setValue(settings.value("port", 8000).toInt());
    }

    QLineEdit *modelEdit = findChild<QLineEdit*>("modelEdit");
    if (modelEdit) {
        modelEdit->setText(settings.value("yolo_model", "yolov8n.pt").toString());
    }

    QSpinBox *confidenceSpin = findChild<QSpinBox*>("confidenceSpin");
    if (confidenceSpin) {
        confidenceSpin->setValue(settings.value("confidence", 45).toInt());
    }
}

void SettingsDialog::saveSettings()
{
    QSettings settings("AI-Cam", "GUI");

    QLineEdit *hostEdit = findChild<QLineEdit*>("hostEdit");
    if (hostEdit) {
        settings.setValue("host", hostEdit->text());
    }

    QSpinBox *portSpin = findChild<QSpinBox*>("portSpin");
    if (portSpin) {
        settings.setValue("port", portSpin->value());
    }

    QLineEdit *modelEdit = findChild<QLineEdit*>("modelEdit");
    if (modelEdit) {
        settings.setValue("yolo_model", modelEdit->text());
    }

    QSpinBox *confidenceSpin = findChild<QSpinBox*>("confidenceSpin");
    if (confidenceSpin) {
        settings.setValue("confidence", confidenceSpin->value());
    }
}

void SettingsDialog::onSaveClicked()
{
    saveSettings();
    accept();
}

void SettingsDialog::onCancelClicked()
{
    reject();
}
