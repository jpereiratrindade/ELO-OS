// SPDX-License-Identifier: GPL-3.0-only
// Adapted from ELO src/perception, retaining local-only frame processing.
#pragma once

#include "CameraDevice.hpp"

#include <QImage>
#include <QObject>
#include <QString>
#include <QVector>

#include <memory>

namespace elo::perception {

/// @brief Continuously captures transient frames, detects faces and produces
/// embeddings only after biometric authorization.
class VisionService final : public QObject {
    Q_OBJECT

public:
    VisionService(
        CameraDevice camera,
        QString detector_model_path,
        QString recognizer_model_path,
        QObject* parent = nullptr);
    ~VisionService() override;

    VisionService(const VisionService&) = delete;
    VisionService& operator=(const VisionService&) = delete;

    void start();
    void stop();

public slots:
    void setBiometricAuthorized(bool authorized);
    void setRecognitionConfirmed(bool confirmed);

signals:
    void frameReady(const QImage& frame);
    void observationProcessed();
    void facePresenceChanged(bool present);
    void attentionChanged(bool engaged, double dwell_time_seconds);
    void faceEmbeddingReady(const QVector<float>& embedding, double quality);
    void statusChanged(const QString& status);
    void failure(const QString& message);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace elo::perception
