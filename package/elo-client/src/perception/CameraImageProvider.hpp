// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <QQuickImageProvider>
#include <QMutex>
#include <QMutexLocker>
class CameraImageProvider final : public QQuickImageProvider {
 public:
  CameraImageProvider() : QQuickImageProvider(Image) {}
  QImage requestImage(const QString&, QSize* size, const QSize& requested) override {
    QMutexLocker lock(&mutex_);
    if (size) *size = frame_.size();
    return requested.isValid() ? frame_.scaled(requested, Qt::KeepAspectRatio, Qt::SmoothTransformation) : frame_;
  }
  void updateFrame(const QImage& frame) {
    QMutexLocker lock(&mutex_);
    frame_ = frame.copy();
  }
 private:
  QMutex mutex_;
  QImage frame_;
};
