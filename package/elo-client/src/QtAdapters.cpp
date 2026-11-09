// SPDX-License-Identifier: GPL-3.0-only
#include "QtAdapters.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStringList>
#include <ifaddrs.h>
#include <net/if.h>
#include <sys/socket.h>
#include <time.h>

namespace {
constexpr qsizetype max_content = 256 * 1024;
QByteArray bounded_file(const QString& path, qsizetype limit) {
  if (QFileInfo(path).isSymLink()) return {};
  QFile file(path);
  if (!file.open(QIODevice::ReadOnly)) return {};
  const auto data = file.read(limit + 1);
  return data.size() <= limit ? data : QByteArray{};
}
bool keys(const QJsonObject& object, QStringList expected) {
  auto actual = object.keys();
  expected.sort();
  actual.sort();
  return actual == expected;
}
QString text(std::string_view value) {
  return QString::fromUtf8(value.data(), static_cast<qsizetype>(value.size()));
}
}
elo::StoredContent QtLocalStore::read_active() const {
  const auto pointer_path = root_ + "/active.json";
  if (!QFileInfo::exists(pointer_path)) return {elo::LoadStatus::missing, {}};
  const auto pointer = QJsonDocument::fromJson(bounded_file(pointer_path, 4096)).object();
  if (!keys(pointer, {"bundle"}) || !pointer["bundle"].isString()) return {elo::LoadStatus::invalid, {}};
  const auto bundle = pointer["bundle"].toString();
  static const QRegularExpression identifier(QStringLiteral("^[0-9a-f]{64}$"));
  if (!identifier.match(bundle).hasMatch()) return {elo::LoadStatus::invalid, {}};
  const auto directory = root_ + "/bundles/" + bundle;
  if (QFileInfo(root_).isSymLink() || QFileInfo(root_ + "/bundles").isSymLink() || QFileInfo(directory).isSymLink())
    return {elo::LoadStatus::invalid, {}};
  const auto manifest = QJsonDocument::fromJson(bounded_file(directory + "/manifest.json", 4096)).object();
  if (!keys(manifest, {"schema", "file", "size", "sha256"}) || manifest["schema"].toDouble(-1) != 1
      || manifest["file"].toString() != "presentation.json" || manifest["sha256"].toString() != bundle
      || !manifest["size"].isDouble()) return {elo::LoadStatus::invalid, {}};
  const auto expected = manifest["size"].toDouble(-1);
  if (expected < 1 || expected > max_content) return {elo::LoadStatus::invalid, {}};
  const auto data = bounded_file(directory + "/presentation.json", max_content);
  if (data.size() != expected || QCryptographicHash::hash(data, QCryptographicHash::Sha256).toHex() != bundle.toLatin1())
    return {elo::LoadStatus::invalid, {}};
  return {elo::LoadStatus::loaded, std::string(data.constData(), static_cast<std::size_t>(data.size()))};
}
elo::LoadResult JsonCatalog::load() {
  const auto stored = store_.read_active();
  if (stored.status != elo::LoadStatus::loaded) return {stored.status, {}};
  const auto json = QJsonDocument::fromJson(QByteArray::fromStdString(stored.utf8)).object();
  if (!keys(json, {"schema", "id", "name", "version", "pages"}) || json["schema"].toDouble(-1) != 1
      || !json["id"].isString() || !json["name"].isString() || !json["version"].isString()
      || !json["pages"].isArray()) return {elo::LoadStatus::invalid, {}};
  elo::Fixture fixture{json["id"].toString().toStdString(), json["name"].toString().toStdString(),
                       json["version"].toString().toStdString(), {}};
  const auto pages = json["pages"].toArray();
  if (pages.isEmpty() || pages.size() > 32) return {elo::LoadStatus::invalid, {}};
  for (const auto& value : pages) {
    const auto page = value.toObject();
    if (!keys(page, {"title", "body"}) || !page["title"].isString() || !page["body"].isString())
      return {elo::LoadStatus::invalid, {}};
    fixture.pages.push_back({page["title"].toString().toStdString(), page["body"].toString().toStdString()});
  }
  return {elo::LoadStatus::loaded, std::move(fixture)};  // Core also checks version/text limits.
}
bool LinuxNetworkStatus::available() const {
  ifaddrs* addresses = nullptr;
  if (getifaddrs(&addresses) != 0) return false;
  bool available = false;
  for (auto* entry = addresses; entry; entry = entry->ifa_next) {
    if (!entry->ifa_addr || (entry->ifa_flags & IFF_LOOPBACK)) continue;
    const auto family = entry->ifa_addr->sa_family;
    if ((family == AF_INET || family == AF_INET6) && (entry->ifa_flags & IFF_UP) && (entry->ifa_flags & IFF_RUNNING))
      available = true;
  }
  freeifaddrs(addresses);
  return available;
}
std::uint64_t BootClock::now_ms() const {
  timespec time{};
  if (clock_gettime(CLOCK_BOOTTIME, &time) != 0) qFatal("CLOCK_BOOTTIME unavailable");
  return static_cast<std::uint64_t>(time.tv_sec) * 1000 + static_cast<std::uint64_t>(time.tv_nsec) / 1000000;
}
void QtDiagnostics::transition(elo::State from, elo::State to) {
  qInfo().noquote() << "elo-client transition=" + text(elo::state_name(from)) + "->" + text(elo::state_name(to));
}
QtRuntime::QtRuntime(QQuickWindow& window, ClientModel& model, const elo::Clock& clock,
                     const elo::NetworkStatus& network, QString health_file, QString token)
    : window_(window), model_(model), clock_(clock), network_(network),
      health_file_(std::move(health_file)), token_(std::move(token)) {
  timer_.setInterval(2000);
  QObject::connect(&timer_, &QTimer::timeout, this, [this] { sample(); });
  QObject::connect(&window_, &QQuickWindow::frameSwapped, this, [this] {
    model_.presentationReady();
    record_frame();
  }, Qt::QueuedConnection);
}
void QtRuntime::start() {
  model_.setNetworkAvailable(network_.available());
  model_.start();
  timer_.start();
  window_.update();
}
void QtRuntime::sample() {
  model_.setNetworkAvailable(network_.available());
  window_.update();  // Challenge the presentation path, even for a static page.
}
void QtRuntime::record_frame() {
  presentation_.presented(clock_.now_ms());
  if (health_file_.isEmpty()) return;
  const elo::PresentationPort& port = presentation_;
  const auto frame = port.last_frame();
  const auto record = QStringLiteral("ELO_HEALTH_V1 %1 %2 %3 %4 %5 %6 %7\n")
      .arg(token_).arg(QCoreApplication::applicationPid())
      .arg(static_cast<qulonglong>(frame.at_ms)).arg(static_cast<qulonglong>(frame.sequence))
      .arg(model_.state()).arg(model_.pageNumber()).arg(QString::fromLatin1(model_.presentationDigest())).toUtf8();
  QSaveFile file(health_file_);
  if (!file.open(QIODevice::WriteOnly) || !file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner)
      || file.write(record) != record.size() || !file.commit()) {
    qCritical() << "elo-client: cannot publish presentation health";
    QCoreApplication::exit(3);
  }
}
