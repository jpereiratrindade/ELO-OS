// SPDX-License-Identifier: GPL-3.0-only
#include "QtAdapters.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QImageReader>
#include <QBuffer>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStringList>
#include <QUrl>
#include <QMap>
#include <ifaddrs.h>
#include <net/if.h>
#include <sys/socket.h>
#include <time.h>

namespace {
constexpr qsizetype max_content = 32 * 1024 * 1024;
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
  if ((!keys(json, {"schema", "id", "name", "version", "pages"})
       && !keys(json, {"schema", "id", "name", "version", "pages", "exposure_seconds"})) || json["schema"].toDouble(-1) != 1
      || !json["id"].isString() || !json["name"].isString() || !json["version"].isString()
      || !json["pages"].isArray()) return {elo::LoadStatus::invalid, {}};
  elo::Fixture fixture{json["id"].toString().toStdString(), json["name"].toString().toStdString(),
                       json["version"].toString().toStdString(), {}};
  if (json.contains("exposure_seconds")) {
    const auto seconds = json["exposure_seconds"].toDouble(-1);
    if ((fixture.version != "4" && fixture.version != "5") || seconds < 5 || seconds > 3600 || seconds != static_cast<int>(seconds))
      return {elo::LoadStatus::invalid, {}};
    fixture.exposure_seconds = static_cast<int>(seconds);
  }
  const auto pages = json["pages"].toArray();
  if (pages.isEmpty() || pages.size() > 32) return {elo::LoadStatus::invalid, {}};
  for (const auto& value : pages) {
    const auto page = value.toObject();
    auto fields = page.keys();
    for (const auto& key : {"title", "body", "image", "interaction", "media"}) fields.removeAll(key);
    if (!fields.isEmpty() || !page["title"].isString() || !page["body"].isString())
      return {elo::LoadStatus::invalid, {}};
    fixture.pages.push_back({page["title"].toString().toStdString(), page["body"].toString().toStdString()});
    if (page.contains("interaction")) {
      if ((fixture.version != "3" && fixture.version != "4" && fixture.version != "5") || !page["interaction"].isString()
          || (page["interaction"] != "none" && page["interaction"] != "reveal")) return {elo::LoadStatus::invalid, {}};
      fixture.pages.back().interaction = page["interaction"].toString().toStdString();
    }
    if (page.contains("media")) {
#ifndef ELO_HAS_MULTIMEDIA
      return {elo::LoadStatus::invalid, {}};
#else
      const auto media = page["media"].toObject();
      if (fixture.version != "5" || !keys(media, {"kind", "mime", "sha256", "base64"})
          || !media["base64"].isString() || !media_cache_.isValid()) return {elo::LoadStatus::invalid, {}};
      const auto kind = media["kind"].toString();
      const auto mime = media["mime"].toString();
      const QMap<QString, QString> formats{{"audio/wav", "wav"}, {"audio/mpeg", "mp3"}, {"audio/ogg", "ogg"},
                                         {"video/mp4", "mp4"}, {"video/webm", "webm"}};
      if (!formats.contains(mime) || (kind != "audio" && kind != "video") || !mime.startsWith(kind + "/")
          || (kind == "video" && page.contains("image"))) return {elo::LoadStatus::invalid, {}};
      const auto encoded = media["base64"].toString().toLatin1();
      if (encoded.size() > 12 * 1024 * 1024) return {elo::LoadStatus::invalid, {}};
      const auto raw = QByteArray::fromBase64(encoded, QByteArray::AbortOnBase64DecodingErrors);
      const auto hash = QCryptographicHash::hash(raw, QCryptographicHash::Sha256).toHex();
      const bool signature = mime == "audio/wav" ? raw.startsWith("RIFF") && raw.mid(8, 4) == "WAVE"
          : mime == "audio/mpeg" ? raw.startsWith("ID3") || (raw.size() > 1 && quint8(raw[0]) == 255 && (quint8(raw[1]) & 224) == 224)
          : mime == "audio/ogg" ? raw.startsWith("OggS")
          : mime == "video/mp4" ? raw.mid(4, 4) == "ftyp" : raw.startsWith(QByteArray::fromHex("1a45dfa3"));
      if (raw.isEmpty() || raw.size() > 8 * 1024 * 1024 || !signature || hash != media["sha256"].toString().toLatin1())
        return {elo::LoadStatus::invalid, {}};
      const auto path = media_cache_.filePath(QString::fromLatin1(hash) + '.' + formats[mime]);
      if (QFileInfo::exists(path)) {
        if (bounded_file(path, 8 * 1024 * 1024) != raw) return {elo::LoadStatus::invalid, {}};
      } else {
        QSaveFile file(path);
        if (!file.open(QIODevice::WriteOnly) || !file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner)
            || file.write(raw) != raw.size() || !file.commit()) return {elo::LoadStatus::invalid, {}};
      }
      auto& output = fixture.pages.back();
      output.media_source = QUrl::fromLocalFile(path).toString().toStdString();
      output.media_kind = kind.toStdString(); output.media_hash = hash.toStdString();
#endif
    }
    if (page.contains("image")) {
      const auto image = page["image"].toObject();
      if ((fixture.version != "2" && fixture.version != "3" && fixture.version != "4" && fixture.version != "5") || !keys(image, {"mime", "sha256", "base64", "alt"})
          || !image["base64"].isString() || !image["alt"].isString()) return {elo::LoadStatus::invalid, {}};
      const auto mime = image["mime"].toString();
      if (mime != "image/png" && mime != "image/jpeg") return {elo::LoadStatus::invalid, {}};
      const auto encoded = image["base64"].toString().toLatin1();
      if (encoded.size() > 2800000) return {elo::LoadStatus::invalid, {}};
      auto raw = QByteArray::fromBase64(encoded, QByteArray::AbortOnBase64DecodingErrors);
      if (raw.isEmpty() || raw.size() > 2 * 1024 * 1024
          || QCryptographicHash::hash(raw, QCryptographicHash::Sha256).toHex() != image["sha256"].toString().toLatin1())
        return {elo::LoadStatus::invalid, {}};
      QBuffer buffer(&raw);
      buffer.open(QIODevice::ReadOnly);
      QImageReader reader(&buffer, mime == "image/png" ? "png" : "jpeg");
      const auto size = reader.size();
      if (!size.isValid() || size.width() > 4096 || size.height() > 4096
          || static_cast<qint64>(size.width()) * size.height() > 8 * 1024 * 1024 || reader.read().isNull())
        return {elo::LoadStatus::invalid, {}};
      auto& output = fixture.pages.back();
      output.image_source = ("data:" + mime.toLatin1() + ";base64," + raw.toBase64()).toStdString();
      output.image_alt = image["alt"].toString().toStdString();
      output.image_hash = image["sha256"].toString().toStdString();
    }
  }
  fixture.content_hash = QCryptographicHash::hash(QByteArray::fromStdString(stored.utf8), QCryptographicHash::Sha256).toHex().toStdString();
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
  QObject::connect(&model_, &ClientModel::changed, &window_, [this] { window_.update(); });
  QObject::connect(&timer_, &QTimer::timeout, this, [this] { sample(); });
  // During synchronization the GUI thread is blocked. Copy identity with the
  // scene being rendered, rather than reading newer model state after a queued frame.
  QObject::connect(&window_, &QQuickWindow::beforeSynchronizing, this, [this] {
    rendering_media_ready_ = window_.property("contentReady").toBool();
    rendering_page_ = model_.presentationDigest();
    rendering_content_ = model_.contentDigest();
  }, Qt::DirectConnection);
  QObject::connect(&window_, &QQuickWindow::frameSwapped, this, [this] {
    const bool ready = rendering_media_ready_;
    const auto page = rendering_page_;
    const auto content = rendering_content_;
    QMetaObject::invokeMethod(this, [this, page, content, ready] {
      if (!ready) return;
      if (page != model_.presentationDigest() || content != model_.contentDigest()) return;
      model_.presentationReady();
      model_.confirmPresented(content);
      record_frame();
    }, Qt::QueuedConnection);
  }, Qt::DirectConnection);
}
void QtRuntime::start() {
  model_.setNetworkAvailable(network_.available());
  model_.start();
  timer_.start();
  window_.update();
}
void QtRuntime::sample() {
  model_.checkContent();
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
