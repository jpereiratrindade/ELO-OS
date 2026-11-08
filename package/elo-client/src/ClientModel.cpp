// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include <QDebug>
namespace {
QString text(std::string_view value) {
  return QString::fromUtf8(value.data(), static_cast<qsizetype>(value.size()));
}
}
QString ClientModel::state() const { return text(client_.state_name()); }
QString ClientModel::title() const { return text(client_.page().title); }
QString ClientModel::body() const { return text(client_.page().body); }
QString ClientModel::fixtureLabel() const {
  if (client_.fixture().id.empty()) return "Fixture não carregada";
  return text(client_.fixture().name) + " · fixture v" + text(client_.fixture().version);
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
