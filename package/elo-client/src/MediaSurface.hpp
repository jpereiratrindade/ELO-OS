// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <QQuickPaintedItem>
#include <QImage>
#include <QUrl>
#include <memory>
class MediaSurface : public QQuickPaintedItem {
  Q_OBJECT
  Q_PROPERTY(QUrl source READ source WRITE setSource NOTIFY sourceChanged)
  Q_PROPERTY(QString kind READ kind WRITE setKind NOTIFY kindChanged)
  Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)
  Q_PROPERTY(bool muted READ muted WRITE setMuted NOTIFY mutedChanged)
  Q_PROPERTY(bool ready READ ready NOTIFY stateChanged)
  Q_PROPERTY(QString error READ error NOTIFY stateChanged)
  Q_PROPERTY(qint64 position READ position NOTIFY progressChanged)
  Q_PROPERTY(qint64 duration READ duration NOTIFY progressChanged)
 public:
  explicit MediaSurface(QQuickItem* parent = nullptr);
  ~MediaSurface() override;
  void paint(QPainter* painter) override;
  Q_INVOKABLE void restart();
  QUrl source() const { return source_; }
  QString kind() const { return kind_; }
  bool active() const { return active_; }
  bool muted() const { return muted_; }
  bool ready() const { return ready_; }
  QString error() const { return error_; }
  qint64 position() const;
  qint64 duration() const;
  void setSource(QUrl source);
  void setKind(QString kind);
  void setActive(bool active);
  void setMuted(bool muted);
 signals:
  void sourceChanged();
  void kindChanged();
  void activeChanged();
  void mutedChanged();
  void stateChanged();
  void progressChanged();
  void finished();
 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
  QUrl source_;
  QString kind_;
  QImage frame_;
  QString error_;
  bool ready_ = true;
  bool active_ = true;
  bool muted_ = false;
  bool ended_ = false;
};
void registerMediaTypes();
