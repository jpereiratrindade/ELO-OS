// SPDX-License-Identifier: GPL-3.0-only
#include "ContentSync.hpp"
#include "QtAdapters.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkRequest>
#include <QNetworkProxy>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSslCertificate>
#include <QSslSocket>
#include <QSslError>
#include <QDebug>
#include <QTemporaryDir>
#include <QStorageInfo>
#include <QUuid>
#include <algorithm>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {
constexpr qsizetype limit = 16 * 1024 * 1024;
struct Descriptor {
  int fd;
  ~Descriptor() { if (fd >= 0) ::close(fd); }
};
QByteArray credential(const QString& path) {
  Descriptor handle{::open(QFile::encodeName(path).constData(), O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)};
  struct stat info{};
  if (handle.fd < 0 || ::fstat(handle.fd, &info) || !S_ISREG(info.st_mode) || (info.st_mode & 0077)) return {};
  QFile file;
  if (!file.open(handle.fd, QIODevice::ReadOnly)) return {};
  auto token = file.read(257).trimmed();
  static const QRegularExpression valid(QStringLiteral("^[A-Za-z0-9_-]{32,128}$"));
  return valid.match(QString::fromLatin1(token)).hasMatch() ? token : QByteArray{};
}
bool syncDirectory(const QString& path) {
  Descriptor dir{::open(QFile::encodeName(path).constData(), O_RDONLY | O_DIRECTORY | O_CLOEXEC)};
  return dir.fd >= 0 && ::fsync(dir.fd) == 0;
}
bool writeFile(const QString& path, const QByteArray& bytes) {
  QSaveFile file(path);
  return file.open(QIODevice::WriteOnly)
      && file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner)
      && file.write(bytes) == bytes.size() && file.flush()
      && ::fsync(file.handle()) == 0 && file.commit();
}
// Return 0 on failure, 1 on success, 2 when publication durability is uncertain.
int publish(const QString& root, const QByteArray& bytes, const QByteArray& digest) {
  struct MemoryStore : elo::LocalStore {
    QByteArray data;
    elo::StoredContent read_active() const override { return {elo::LoadStatus::loaded, data.toStdString()}; }
  } store;
  store.data = bytes;
  JsonCatalog catalog(store);
  elo::Client candidate(&catalog);
  candidate.start();
  if (!candidate.error().empty() || !candidate.page_count()) return 0;
  const auto root_parent = QFileInfo(root).dir().absolutePath();
  if (QFileInfo(root).isSymLink() || !QFileInfo(root_parent).isDir()) return 0;
  const bool new_root = !QFileInfo::exists(root);
  if (!QDir().mkpath(root)) return 0;
  if (new_root && (!QFile::setPermissions(root, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner)
                   || !syncDirectory(root_parent))) return 0;
  const auto bundles = root + "/bundles";
  if (QFileInfo(bundles).isSymLink() || !QDir().mkpath(bundles)) return 0;
  Descriptor lock{::open(QFile::encodeName(root + "/.activation.lock").constData(),
                        O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600)};
  if (lock.fd < 0 || ::flock(lock.fd, LOCK_EX | LOCK_NB)) return 0;
  const auto target = bundles + "/" + QString::fromLatin1(digest);
  if (QFileInfo(target).isSymLink()) return 0;
  const auto manifest = QJsonDocument(QJsonObject{{"schema", 1}, {"file", "presentation.json"},
                       {"size", static_cast<int>(bytes.size())}, {"sha256", QString::fromLatin1(digest)}}).toJson();
  if (QFileInfo::exists(target)) {
    // Verify the complete existing bundle using the same reader as the UI.
    QFile content(target + "/presentation.json");
    QFile metadata(target + "/manifest.json");
    if (QFileInfo(content).isSymLink() || QFileInfo(metadata).isSymLink()
        || !content.open(QIODevice::ReadOnly) || content.read(8 * 1024 * 1024 + 1) != bytes
        || !metadata.open(QIODevice::ReadOnly)) return 0;
    const auto obj = QJsonDocument::fromJson(metadata.read(4097)).object();
    if (obj.size() != 4 || obj["schema"].toDouble(-1) != 1 || obj["file"] != "presentation.json"
        || obj["size"].toDouble(-1) != bytes.size() || obj["sha256"] != QString::fromLatin1(digest)) return 0;
  } else {
    const QStorageInfo volume(root);
    if (!volume.isValid() || volume.bytesAvailable() < bytes.size() * 2 + 4 * 1024 * 1024
        || QDir(bundles).entryList(QDir::Dirs | QDir::NoDotAndDotDot).size() >= 32
        || QDir(root).entryList({".download-*"}, QDir::Dirs | QDir::Hidden | QDir::NoDotAndDotDot).size() >= 4) return 0;
    QTemporaryDir staging(root + "/.download-XXXXXX");
    if (!staging.isValid() || !writeFile(staging.path() + "/presentation.json", bytes)
        || !writeFile(staging.path() + "/manifest.json", manifest) || !syncDirectory(staging.path())) return 0;
    if (!QDir().rename(staging.path(), target)) return 0;
  }
  if (!syncDirectory(target) || !syncDirectory(bundles) || !syncDirectory(root)) return 0;
  if (QFileInfo(root + "/active.json").isSymLink()) return 0;
  QFile active(root + "/active.json");
  if (active.open(QIODevice::ReadOnly)) {
    const auto current = QJsonDocument::fromJson(active.read(4097)).object();
    if (current.size() == 1 && current["bundle"].toString().toLatin1() == digest) return 1;
  }
  const auto pointer = QJsonDocument(QJsonObject{{"bundle", QString::fromLatin1(digest)}}).toJson();
  if (!writeFile(root + "/active.json", pointer)) return 0;
  return syncDirectory(root) ? 1 : 2;
}
}
ContentSync::ContentSync(ClientModel& model, QString root, QUrl endpoint, QString token_file,
                         QString ca_file, bool allow_loopback_http)
    : model_(model), root_(std::move(root)), endpoint_(std::move(endpoint)),
      token_file_(std::move(token_file)), ca_file_(std::move(ca_file)), insecure_(allow_loopback_http) {
  session_ = QUuid::createUuid().toString(QUuid::WithoutBraces);
  report_timer_.setSingleShot(true);
  report_deadline_.setSingleShot(true);
  QObject::connect(&report_timer_, &QTimer::timeout, this, [this] { report(); });
  QObject::connect(&report_deadline_, &QTimer::timeout, this, [this] { if (report_reply_) report_reply_->abort(); });
  QObject::connect(&model_, &ClientModel::contentPresented, this, [this](const QByteArray& digest) {
    if (received_.isEmpty()) received_ = digest;  // Validated cache loaded at startup.
    const QJsonObject display{{"publication", model_.publicationName().simplified()},
        {"title", model_.title().simplified()}, {"page", model_.pageNumber()}, {"pages", model_.pageCount()},
        {"mode", model_.autoplay() ? "automatic" : "manual"}, {"exposure_seconds", model_.exposureSeconds()}};
    if (presented_ == digest && display_ == display) return;
    presented_ = digest;
    display_ = display;
    scheduleReport();
  });
  manager_.setProxy(QNetworkProxy::NoProxy);
  timer_.setSingleShot(true);
  deadline_.setSingleShot(true);
  QObject::connect(&timer_, &QTimer::timeout, this, [this] { fetch(); });
  QObject::connect(&deadline_, &QTimer::timeout, this, [this] { if (reply_) reply_->abort(); });
}
QString ContentSync::configure() {
  if (!endpoint_.isValid() || endpoint_.host().isEmpty() || !endpoint_.userInfo().isEmpty()
      || endpoint_.hasQuery() || endpoint_.hasFragment() || endpoint_.path() != "/v1/presentation"
      || !QDir::isAbsolutePath(root_)) return "Invalid distribution endpoint/cache path";
  if (insecure_) {
    if (endpoint_.scheme() != "http" || endpoint_.host() != "127.0.0.1" || !ca_file_.isEmpty())
      return "Development HTTP requires literal 127.0.0.1 and no CA option";
  } else if (endpoint_.scheme() != "https" || !QSslSocket::supportsSsl()) return "HTTPS/TLS required";
  if (!QDir::isAbsolutePath(token_file_)) return "Terminal token file path must be absolute";
  tls_ = QSslConfiguration::defaultConfiguration();
  tls_.setPeerVerifyMode(QSslSocket::VerifyPeer);
  tls_.setProtocol(QSsl::TlsV1_2OrLater);
  if (!ca_file_.isEmpty()) {
    QFile file(ca_file_);
    if (!file.open(QIODevice::ReadOnly) || file.size() > 256 * 1024) return "Invalid CA file";
    const auto certificates = QSslCertificate::fromData(file.readAll());
    if (certificates.isEmpty()) return "Invalid CA certificate";
    tls_.setCaCertificates(certificates);
  }
  return {};
}
void ContentSync::start() { timer_.start(0); }
void ContentSync::fetch() {
  const auto token = credential(token_file_);
  if (token.isEmpty()) { qWarning() << "elo-client credential_unavailable"; fail(); return; }
  model_.setServerStatus(insecure_ ? "Servidor local de teste · consultando publicação"
                                  : "Servidor ELO · consultando publicação");
  QNetworkRequest request(endpoint_);
  request.setRawHeader("Authorization", "Bearer " + token);
  request.setRawHeader("Accept", "application/json");
  request.setRawHeader("X-ELO-Capabilities", "text-v1,image-v2,reveal-v3,autoplay-v4");
  request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::ManualRedirectPolicy);
  request.setAttribute(QNetworkRequest::CacheLoadControlAttribute, QNetworkRequest::AlwaysNetwork);
  request.setSslConfiguration(tls_);
  request.setTransferTimeout(10000);
  response_.clear();
  reply_ = manager_.get(request);
  reply_->setReadBufferSize(limit + 1);
  QObject::connect(reply_, &QNetworkReply::readyRead, this, [this] {
    response_ += reply_->read(limit + 1 - response_.size());
    if (response_.size() > limit) reply_->abort();
  });
  QObject::connect(reply_, &QNetworkReply::finished, this, [this] { finish(); });
  QObject::connect(reply_, &QNetworkReply::sslErrors, this, [](const QList<QSslError>& errors) {
    for (const auto& error : errors) qWarning().noquote() << "elo-client TLS:" << error.errorString();
  });
  deadline_.start(15000);
}
void ContentSync::fail() {
  model_.setServerStatus("Servidor indisponível ou publicação recusada · cache local preservado");
  timer_.start(retry_ms_);
  retry_ms_ = std::min(retry_ms_ * 2, 60000);
}
void ContentSync::finish() {
  deadline_.stop();
  auto* reply = reply_;
  reply_ = nullptr;
  reply->deleteLater();
  response_ += reply->read(limit + 1 - response_.size());
  if (reply->error() != QNetworkReply::NoError || reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() != 200
      || response_.size() > limit || !reply->header(QNetworkRequest::ContentTypeHeader).toString().startsWith("application/json")) {
    qWarning() << "elo-client fetch_failed network=" << int(reply->error())
               << "http=" << reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    fail(); return;
  }
  const auto object = QJsonDocument::fromJson(response_).object();
  const auto payload = object["presentation"].toString().toUtf8();
  const auto digest = QCryptographicHash::hash(payload, QCryptographicHash::Sha256).toHex();
  if (object.size() != 5 || object["schema"].toDouble(-1) != 1 || !object["source"].isObject()
      || payload.isEmpty() || payload.size() > 8 * 1024 * 1024 || object["size"].toDouble(-1) != payload.size()
      || object["sha256"].toString().toLatin1() != digest) { fail(); return; }
  const auto result = publish(root_, payload, digest);
  if (!result) { fail(); return; }
  if (result == 2) {
    model_.setServerStatus("Publicação recebida · durabilidade do cache inconclusiva");
    timer_.start(5000);
    return;
  }
  received_ = digest;
  scheduleReport();
  model_.setServerStatus(insecure_ ? "Servidor local de teste · conteúdo recebido (HTTP)"
                                  : "Servidor ELO verificado · conteúdo recebido (HTTPS)");
  if (model_.canRetry()) model_.retry();
  else model_.checkContent();
  retry_ms_ = 5000;
  timer_.start(30000);
}

void ContentSync::scheduleReport() {
  report_dirty_ = true;
  if (!report_reply_) report_timer_.start(50);
}
void ContentSync::report() {
  if (report_reply_ || (received_.isEmpty() && presented_.isEmpty())) return;
  const auto token = credential(token_file_);
  if (token.isEmpty()) {
    report_timer_.start(report_retry_ms_);
    report_retry_ms_ = std::min(report_retry_ms_ * 2, 60000);
    return;
  }
  auto url = endpoint_;
  url.setPath("/v1/receipt");
  QNetworkRequest request(url);
  request.setRawHeader("Authorization", "Bearer " + token);
  request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
  request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::ManualRedirectPolicy);
  request.setSslConfiguration(tls_);
  request.setTransferTimeout(10000);
  QJsonObject report{{"schema", display_.isEmpty() ? 1 : 2}, {"session", session_},
      {"sequence", static_cast<qint64>(++report_sequence_)},
      {"received_sha256", QString::fromLatin1(received_)},
      {"presented_sha256", QString::fromLatin1(presented_)}};
  if (!display_.isEmpty()) report.insert("display", display_);
  const auto payload = QJsonDocument(report).toJson(QJsonDocument::Compact);
  report_dirty_ = false;
  report_reply_ = manager_.post(request, payload);
  report_reply_->setReadBufferSize(4097);
  QObject::connect(report_reply_, &QNetworkReply::readyRead, this, [this] {
    if (report_reply_->bytesAvailable() > 4096) report_reply_->abort();
  });
  QObject::connect(report_reply_, &QNetworkReply::finished, this, [this] {
    report_deadline_.stop();
    auto* reply = report_reply_;
    report_reply_ = nullptr;
    const bool ok = reply->error() == QNetworkReply::NoError
        && reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200
        && reply->read(4097).size() <= 4096;
    reply->deleteLater();
    if (ok) {
      report_retry_ms_ = 5000;
      report_timer_.start(report_dirty_ ? 50 : 30000);
    } else {
      qWarning() << "elo-client report_failed network=" << int(reply->error())
                 << "http=" << reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
      report_timer_.start(report_retry_ms_);
      report_retry_ms_ = std::min(report_retry_ms_ * 2, 60000);
    }
  });
  report_deadline_.start(15000);
}
