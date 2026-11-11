// SPDX-License-Identifier: GPL-3.0-only
#include "MediaSurface.hpp"
#include <QPainter>
#include <QQmlEngine>
#ifdef ELO_HAS_MULTIMEDIA
#include <QMediaPlayer>
#include <QAudioOutput>
#include <QVideoSink>
#include <QVideoFrame>
struct MediaSurface::Impl { QMediaPlayer player; QAudioOutput audio; QVideoSink video; };
#else
struct MediaSurface::Impl {};
#endif
MediaSurface::MediaSurface(QQuickItem* parent) : QQuickPaintedItem(parent), impl_(std::make_unique<Impl>()) {
#ifdef ELO_HAS_MULTIMEDIA
  impl_->player.setAudioOutput(&impl_->audio);
  impl_->player.setVideoSink(&impl_->video);
  connect(&impl_->player, &QMediaPlayer::positionChanged, this, &MediaSurface::progressChanged);
  connect(&impl_->player, &QMediaPlayer::durationChanged, this, &MediaSurface::progressChanged);
  connect(&impl_->player, &QMediaPlayer::errorOccurred, this, [this](QMediaPlayer::Error, const QString& message) {
    ready_ = false; error_ = message; emit stateChanged();
  });
  connect(&impl_->player, &QMediaPlayer::mediaStatusChanged, this, [this](QMediaPlayer::MediaStatus status) {
    if (status == QMediaPlayer::LoadedMedia && kind_ == "audio") { ready_ = true; emit stateChanged(); }
    if (status == QMediaPlayer::EndOfMedia) { ended_ = true; emit finished(); }
  });
  connect(&impl_->video, &QVideoSink::videoFrameChanged, this, [this](const QVideoFrame& frame) {
    if (!frame.isValid()) return;
    frame_ = frame.toImage();
    if (!frame_.isNull()) { ready_ = true; if (!active_) impl_->player.pause(); emit stateChanged(); update(); }
  });
#endif
}
MediaSurface::~MediaSurface() = default;
void MediaSurface::paint(QPainter* painter) {
  if (frame_.isNull()) return;
  auto size = frame_.size(); size.scale(boundingRect().size().toSize(), Qt::KeepAspectRatio);
  painter->drawImage(QRectF((width() - size.width()) / 2, (height() - size.height()) / 2, size.width(), size.height()), frame_);
}
void MediaSurface::setSource(QUrl source) {
  if (source_ == source) return;
#ifdef ELO_HAS_MULTIMEDIA
  impl_->player.stop();
#endif
  source_ = std::move(source); ended_ = false; frame_ = {}; error_.clear(); ready_ = source_.isEmpty(); update();
#ifdef ELO_HAS_MULTIMEDIA
  // Catalog materializes only hash-verified files. Network media is never fetched by the player.
  if (!source_.isEmpty() && !source_.isLocalFile()) { error_ = "Mídia deve estar no cache local"; ready_ = false; }
  else { impl_->audio.setMuted(muted_ || !active_); impl_->player.setSource(source_); if (!source_.isEmpty() && (active_ || kind_ == "video")) impl_->player.play(); }
#else
  if (!source_.isEmpty()) error_ = "Cliente compilado sem suporte audiovisual";
#endif
  emit sourceChanged(); emit stateChanged();
}
void MediaSurface::setKind(QString kind) { if (kind_ != kind) { kind_ = std::move(kind); emit kindChanged(); } }
void MediaSurface::setActive(bool active) {
  if (active_ == active) return;
  active_ = active;
#ifdef ELO_HAS_MULTIMEDIA
  impl_->audio.setMuted(muted_ || !active_);
  if (!source_.isEmpty() && error_.isEmpty()) { if (active_ && !ended_) impl_->player.play(); else if (ready_ || kind_ != "video") impl_->player.pause(); }
#endif
  emit activeChanged();
}
void MediaSurface::setMuted(bool muted) {
  if (muted_ == muted) return;
  muted_ = muted;
#ifdef ELO_HAS_MULTIMEDIA
  impl_->audio.setMuted(muted_ || !active_);
#endif
  emit mutedChanged();
}
qint64 MediaSurface::position() const {
#ifdef ELO_HAS_MULTIMEDIA
  return impl_->player.position();
#else
  return 0;
#endif
}
qint64 MediaSurface::duration() const {
#ifdef ELO_HAS_MULTIMEDIA
  return impl_->player.duration();
#else
  return 0;
#endif
}
void registerMediaTypes() { qmlRegisterType<MediaSurface>("Elo.Media", 1, 0, "MediaSurface"); }

void MediaSurface::restart() {
  if (source_.isEmpty()) return;
  const auto source = source_; source_ = QUrl{}; setSource(source);
}
