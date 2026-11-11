// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "ClientModel.hpp"
#include "core/ports.hpp"
#include <QObject>
#include <QTimer>
#include <utility>
#include <QTemporaryDir>
class QQuickWindow;

class QtLocalStore final : public elo::LocalStore {
 public:
  explicit QtLocalStore(QString root) : root_(std::move(root)) {}
  elo::StoredContent read_active() const override;
 private:
  QString root_;
};
class JsonCatalog final : public elo::ContentCatalog {
 public:
  explicit JsonCatalog(const elo::LocalStore& store) : store_(store) {}
  elo::LoadResult load() override;
 private:
  const elo::LocalStore& store_;
  QTemporaryDir media_cache_;
};
class LinuxNetworkStatus final : public elo::NetworkStatus {
 public:
  bool available() const override;
};
class BootClock final : public elo::Clock {
 public:
  std::uint64_t now_ms() const override;
};
class QtDiagnostics final : public elo::Diagnostics {
 public:
  void transition(elo::State from, elo::State to) override;
};
class FrameTracker final : public elo::PresentationPort {
 public:
  elo::PresentedFrame last_frame() const override { return frame_; }
  void presented(std::uint64_t now) { ++frame_.sequence; frame_.at_ms = now; }
 private:
  elo::PresentedFrame frame_;
};
class QtRuntime final : public QObject {
 public:
  QtRuntime(QQuickWindow& window, ClientModel& model, const elo::Clock& clock,
            const elo::NetworkStatus& network, QString health_file = {}, QString token = {});
  void start();
 private:
  void sample();
  void record_frame();
  QQuickWindow& window_;
  ClientModel& model_;
  const elo::Clock& clock_;
  const elo::NetworkStatus& network_;
  FrameTracker presentation_;
  QTimer timer_;
  bool rendering_media_ready_ = true;
  QByteArray rendering_page_;
  QByteArray rendering_content_;
  QString health_file_;
  QString token_;
};
