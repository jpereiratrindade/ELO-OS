// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "core/client.hpp"
#include <QObject>
#include <QTimer>
#include <QByteArray>
#include <QString>

class ClientModel : public QObject {
  Q_OBJECT
  Q_PROPERTY(QString state READ state NOTIFY changed)
  Q_PROPERTY(QString title READ title NOTIFY changed)
  Q_PROPERTY(QString body READ body NOTIFY changed)
  Q_PROPERTY(QString imageSource READ imageSource NOTIFY changed)
  Q_PROPERTY(QString mediaSource READ mediaSource NOTIFY changed)
  Q_PROPERTY(QString mediaKind READ mediaKind NOTIFY changed)
  Q_PROPERTY(bool playbackAllowed READ playbackAllowed NOTIFY changed)
  Q_PROPERTY(QString imageAlt READ imageAlt NOTIFY changed)
  Q_PROPERTY(int pageNumber READ pageNumber NOTIFY changed)
  Q_PROPERTY(int pageCount READ pageCount NOTIFY changed)
  Q_PROPERTY(QString fixtureLabel READ fixtureLabel NOTIFY changed)
  Q_PROPERTY(QString error READ error NOTIFY changed)
  Q_PROPERTY(int exposureCycle READ exposureCycle NOTIFY changed)
  Q_PROPERTY(bool autoplay READ autoplay NOTIFY changed)
  Q_PROPERTY(int exposureSeconds READ exposureSeconds NOTIFY changed)
  Q_PROPERTY(bool canNext READ canNext NOTIFY changed)
  Q_PROPERTY(bool canPrevious READ canPrevious NOTIFY changed)
  Q_PROPERTY(bool canReveal READ canReveal NOTIFY changed)
  Q_PROPERTY(bool canRetry READ canRetry NOTIFY changed)
  Q_PROPERTY(QString contentUpdate READ contentUpdate NOTIFY changed)
  Q_PROPERTY(QString connectivity READ connectivity NOTIFY changed)
 public:
  explicit ClientModel(QObject* parent = nullptr, elo::ContentCatalog* catalog = nullptr,
                       elo::Diagnostics* diagnostics = nullptr)
      : QObject(parent), client_(catalog, diagnostics) {
    exposure_timer_.setSingleShot(true);
    exposure_timer_.setTimerType(Qt::PreciseTimer);
    connect(&exposure_timer_, &QTimer::timeout, this, &ClientModel::advanceAutomatically);
    connect(this, &ClientModel::changed, this, [this] {
      if (timed_page_ != pageKey()) { exposure_timer_.stop(); timed_page_.clear(); }
    });
  }
  QString state() const;
  QString title() const;
  QString body() const;
  QString imageSource() const;
  QString imageAlt() const;
  QString mediaSource() const;
  QString mediaKind() const;
  bool playbackAllowed() const { return playback_allowed_; }
  void setPlaybackAllowed(bool allowed);
  Q_INVOKABLE void resumePage(int page);
  Q_INVOKABLE void setMediaDuration(qint64 milliseconds);
  int pageNumber() const { return client_.page_count() ? static_cast<int>(client_.index() + 1) : 0; }
  int pageCount() const { return static_cast<int>(client_.page_count()); }
  QString fixtureLabel() const;
  QString publicationName() const;
  QString error() const;
  int exposureCycle() const { return exposure_cycle_; }
  bool autoplay() const { return client_.fixture().exposure_seconds > 0; }
  int exposureSeconds() const { return client_.fixture().exposure_seconds; }
  bool canNext() const { return client_.can_next(); }
  bool canPrevious() const { return client_.can_previous(); }
  bool canReveal() const { return client_.can_reveal(); }
  bool canRetry() const { return client_.state() == elo::State::error_recoverable; }
  QString connectivity() const;
  void setServerStatus(QString status);
  QString contentUpdate() const;
  void checkContent();
  QByteArray presentationDigest() const;
  QByteArray contentDigest() const;
  void confirmPresented(const QByteArray& digest);
  void setNetworkAvailable(bool available);
  void start();
  void presentationReady();
  Q_INVOKABLE void next();
  Q_INVOKABLE void previous();
  Q_INVOKABLE void reset();
  Q_INVOKABLE void retry();
  Q_INVOKABLE void reveal();
 signals:
  void changed();
  void contentPresented(QByteArray digest);
 private:
  QByteArray pageKey() const;
  void advanceAutomatically();
  elo::Client client_;
  QTimer exposure_timer_;
  int exposure_cycle_ = 0;
  QByteArray timed_page_;
  bool network_available_ = false;
  QString server_status_;
  bool playback_allowed_ = true;
  int paused_exposure_ms_ = 0;
  qint64 media_duration_ms_ = 0;
  int target_exposure_ms_ = 0;
};
