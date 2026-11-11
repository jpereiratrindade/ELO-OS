// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include <QDebug>
#include <QCryptographicHash>
namespace {
QString text(std::string_view value) {
  return QString::fromUtf8(value.data(), static_cast<qsizetype>(value.size()));
}
}
QString ClientModel::state() const { return text(client_.state_name()); }
QString ClientModel::title() const { return text(client_.page().title); }
QString ClientModel::body() const { return text(client_.page().body); }
QString ClientModel::imageSource() const { return text(client_.page().image_source); }
QString ClientModel::mediaSource() const { return text(client_.page().media_source); }
QString ClientModel::mediaKind() const { return text(client_.page().media_kind); }
QString ClientModel::imageAlt() const { return text(client_.page().image_alt); }
QString ClientModel::publicationName() const { return text(client_.fixture().name); }
QString ClientModel::fixtureLabel() const {
  if (client_.fixture().id.empty()) return "Conteúdo não carregado";
  return text(client_.fixture().name) + " · formato local v" + text(client_.fixture().version);
}
QString ClientModel::error() const { return text(client_.error()); }
void ClientModel::start() {
  qInfo().noquote() << "elo-client state=" + state();
  if (client_.start()) {
    emit changed();
    qInfo().noquote() << "elo-client state=" + state();
  }
}
void ClientModel::presentationReady() {
  if (client_.dispatch(elo::PresentationReady{true})) {
    emit changed();
    qInfo().noquote() << "elo-client state=" + state() + " fixture=" + text(client_.fixture().id);
  }
}
void ClientModel::next() { if (client_.next()) emit changed(); }
void ClientModel::previous() { if (client_.previous()) emit changed(); }
void ClientModel::reset() { if (client_.reset()) emit changed(); }
QString ClientModel::connectivity() const {
  if (!server_status_.isEmpty()) return server_status_;
  return network_available_ ? QStringLiteral("Rede local disponível · servidor não verificado")
                            : QStringLiteral("Sem rede local · apresentação independente da rede");
}
void ClientModel::setNetworkAvailable(bool available) {
  if (network_available_ == available) return;
  network_available_ = available;
  client_.dispatch(elo::NetworkChanged{available});
  emit changed();
  qInfo().noquote() << "elo-client network=" + QString(available ? "local-link" : "offline") + " state=" + state();
}
void ClientModel::retry() {
  if (client_.dispatch(elo::Retry{})) {
    emit changed();
    qInfo().noquote() << "elo-client state=" + state();
  }
}
QByteArray ClientModel::presentationDigest() const {
  QByteArray bytes;
  for (const auto& part : {client_.fixture().id, client_.fixture().version,
                           client_.page().title, client_.page().body, client_.page().image_hash, client_.page().media_hash}) {
    if (part.empty()) continue;
    bytes.append(part.data(), static_cast<qsizetype>(part.size()));
    bytes.append('\0');
  }
  return QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex();
}

QString ClientModel::contentUpdate() const {
  switch (client_.content_update()) {
    case elo::ContentUpdate::available:
      return QStringLiteral("Novo conteúdo disponível · Recomeçar para atualizar.");
    case elo::ContentUpdate::rejected:
      return QStringLiteral("Atualização indisponível · conteúdo atual preservado.");
    case elo::ContentUpdate::none: return {};
  }
  return {};
}
void ClientModel::checkContent() {
  const bool updated = client_.dispatch(elo::CheckContent{});
  // Operator explicitly enabled unattended playback. Enter without a local click.
  if (!autoplay() && client_.pending_autoplay()) { reset(); return; }
  if (updated) {
    emit changed();
    qInfo().noquote() << "elo-client content-update=" + contentUpdate();
  }
}

void ClientModel::setServerStatus(QString status) {
  if (server_status_ == status) return;
  server_status_ = std::move(status);
  emit changed();
  qInfo().noquote() << "elo-client distribution=" + server_status_;
}

QByteArray ClientModel::contentDigest() const {
  return QByteArray::fromStdString(client_.fixture().content_hash);
}
void ClientModel::confirmPresented(const QByteArray& digest) {
  if (!client_.usable() || digest.isEmpty() || digest != contentDigest()) return;
  emit contentPresented(digest);
  // Start exposure only after this page's decoded pixels reached a rendered frame.
  if (autoplay() && timed_page_ != pageKey()) {
    timed_page_ = pageKey();
    paused_exposure_ms_ = int(qMax<qint64>(exposureSeconds() * 1000, mediaSource().isEmpty() ? 0 : media_duration_ms_));
    target_exposure_ms_ = paused_exposure_ms_;
    if (playback_allowed_) exposure_timer_.start(paused_exposure_ms_);
  }
}

void ClientModel::reveal() { if (client_.dispatch(elo::Reveal{})) emit changed(); }

QByteArray ClientModel::pageKey() const {
  return contentDigest() + ':' + QByteArray::number(pageNumber()) + ':' + presentationDigest();
}
void ClientModel::advanceAutomatically() {
  if (!autoplay() || !client_.usable()) return;
  timed_page_.clear();
  exposure_cycle_ = (exposure_cycle_ + 1) % 1000000;
  if (client_.can_next()) next();
  else {
    // End of loop is the unattended session boundary for validated updates.
    client_.reset();
    emit changed();
  }
}

void ClientModel::setPlaybackAllowed(bool allowed) {
  if (playback_allowed_ == allowed) return;
  playback_allowed_ = allowed;
  if (!allowed && exposure_timer_.isActive()) {
    paused_exposure_ms_ = exposure_timer_.remainingTime(); exposure_timer_.stop();
  } else if (allowed && !timed_page_.isEmpty() && paused_exposure_ms_ > 0) {
    exposure_timer_.start(paused_exposure_ms_);
  }
  emit changed();
}
void ClientModel::resumePage(int page) {
  if (!client_.usable() || page < 1 || page > pageCount()) return;
  while (pageNumber() < page) if (!client_.next()) break;
  while (pageNumber() > page) if (!client_.previous()) break;
  emit changed();
}

void ClientModel::setMediaDuration(qint64 milliseconds) {
  media_duration_ms_ = qBound<qint64>(qint64(0), milliseconds, qint64(86400000));
  if (!autoplay() || timed_page_.isEmpty() || mediaSource().isEmpty()) return;
  const int required = int(qMax<qint64>(exposureSeconds() * 1000, media_duration_ms_));
  if (required <= target_exposure_ms_) return;
  const int remaining = exposure_timer_.isActive() ? exposure_timer_.remainingTime() : paused_exposure_ms_;
  paused_exposure_ms_ = qMax(0, remaining) + required - target_exposure_ms_;
  target_exposure_ms_ = required;
  if (playback_allowed_) exposure_timer_.start(paused_exposure_ms_);
}
