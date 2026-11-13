// SPDX-License-Identifier: GPL-3.0-only
// Independent root-owned maintenance agent. Only two fixed system actions exist.
#include <QCoreApplication>
#include <QCommandLineParser>
#include <QDateTime>
#include <QDir>
#include <QElapsedTimer>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLockFile>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QProcess>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslSocket>
#include <QTimer>
#include <QUrl>
#include <QUuid>
#include <functional>
#include <memory>
#include <fcntl.h>
#include <unistd.h>

namespace {
QByteArray read(const QString& path) {
  QFile file(path);
  return file.open(QIODevice::ReadOnly) ? file.read(16385).trimmed() : QByteArray{};
}
bool uuid(const QString& value) {
  const auto parsed = QUuid::fromString(value);
  return !parsed.isNull() && parsed.toString(QUuid::WithoutBraces) == value;
}
QJsonObject collectTelemetry() {
  QJsonObject tele;
  const auto tempBytes = read("/sys/class/thermal/thermal_zone0/temp");
  if (!tempBytes.isEmpty()) {
    bool ok = false;
    const qint64 millideg = tempBytes.toLongLong(&ok);
    if (ok && millideg > -40000 && millideg < 150000) {
      tele["cpu_temp_c"] = qRound(millideg / 100.0) / 10.0;
    }
  }
  const auto voltBytes = read("/sys/class/regulator/regulator.2/microvolts");
  if (!voltBytes.isEmpty()) {
    bool ok = false;
    const qint64 microvolts = voltBytes.toLongLong(&ok);
    if (ok && microvolts > 0 && microvolts < 24000000) {
      tele["voltage_v"] = qRound(microvolts / 10000.0) / 100.0;
    }
  }
  const auto loadBytes = read("/proc/loadavg");
  if (!loadBytes.isEmpty()) {
    const auto parts = loadBytes.split(' ');
    if (!parts.isEmpty()) {
      bool ok = false;
      const double load = parts[0].toDouble(&ok);
      if (ok && load >= 0.0 && load <= 256.0) {
        tele["cpu_load_1m"] = qRound(load * 100.0) / 100.0;
      }
    }
  }
  QFile memFile("/proc/meminfo");
  if (memFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
    while (!memFile.atEnd()) {
      const auto line = memFile.readLine();
      if (line.startsWith("MemAvailable:")) {
        const auto parts = line.simplified().split(' ');
        if (parts.size() >= 2) {
          bool ok = false;
          const qint64 kb = parts[1].toLongLong(&ok);
          if (ok && kb >= 0) tele["memory_free_mb"] = qRound(kb / 1024.0);
        }
        break;
      }
    }
  }
  const auto uptimeBytes = read("/proc/uptime");
  if (!uptimeBytes.isEmpty()) {
    const auto parts = uptimeBytes.split(' ');
    if (!parts.isEmpty()) {
      bool ok = false;
      const double uptime = parts[0].toDouble(&ok);
      if (ok && uptime >= 0.0) tele["uptime_seconds"] = qRound(uptime);
    }
  }
  QFile wifiFile("/proc/net/wireless");
  if (wifiFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
    while (!wifiFile.atEnd()) {
      const auto line = wifiFile.readLine();
      if (line.contains("wlan0:")) {
        const auto parts = line.simplified().split(' ');
        if (parts.size() >= 4) {
          QString s = QString::fromLatin1(parts[3]).remove('.');
          bool ok = false;
          const double dbm = s.toDouble(&ok);
          if (ok && dbm < 0.0 && dbm >= -120.0) tele["wifi_rssi_dbm"] = dbm;
        }
        break;
      }
    }
  }
  return tele;
}
class Agent : public QObject {
 public:
  Agent(QString config, QString state) : config_(std::move(config)), state_(std::move(state)), lock_(state_ + "/agent.lock") {}
  bool start() {
    QDir().mkpath(state_);
    QFile::setPermissions(state_, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
    if (!lock_.tryLock(0)) { qCritical("control: another agent owns the state"); return false; }
#ifndef ELO_CONTROL_TEST_EXECUTOR
    if (geteuid() != 0 || !read("/proc/device-tree/model").startsWith("Raspberry Pi")) {
      qCritical("control: system power control requires a Raspberry Pi and root"); return false;
    }
#endif
    boot_ = QString::fromLatin1(read("/proc/sys/kernel/random/boot_id"));
    endpoint_ = QUrl(QString::fromUtf8(read(config_ + "/server.url")));
    token_ = read(config_ + "/terminal.token");
    const auto certs = QSslCertificate::fromPath(config_ + "/ca.pem");
    const auto permissions = QFile::permissions(config_ + "/terminal.token");
    if (!uuid(boot_) || !endpoint_.isValid() || endpoint_.scheme() != "https" || endpoint_.host().isEmpty()
        || !endpoint_.userInfo().isEmpty() || endpoint_.hasQuery() || endpoint_.hasFragment()
        || endpoint_.path() != "/v1/presentation"
        || !QRegularExpression("^[A-Za-z0-9_-]{32,128}$").match(QString::fromLatin1(token_)).hasMatch()
        || permissions & (QFileDevice::ReadGroup | QFileDevice::WriteGroup | QFileDevice::ReadOther | QFileDevice::WriteOther)
        || certs.isEmpty()) { qCritical("control: invalid terminal configuration"); return false; }
    tls_ = QSslConfiguration::defaultConfiguration();
    tls_.setCaCertificates(certs);
    tls_.setPeerVerifyMode(QSslSocket::VerifyPeer);
    const auto ledger = read(state_ + "/consumed.json");
    if (!ledger.isEmpty()) {
      QJsonParseError error;
      const auto doc = QJsonDocument::fromJson(ledger, &error);
      if (error.error != QJsonParseError::NoError || !doc.isArray() || doc.array().size() > 128) return false;
      consumed_ = doc.array();
      for (const auto& id : consumed_) if (!id.isString() || !uuid(id.toString())) return false;
    } else if (QFile::exists(state_ + "/consumed.json")) { qCritical("control: invalid command ledger"); return false; }
    timer_.setInterval(5000);
    connect(&timer_, &QTimer::timeout, this, [this] { poll(); });
    timer_.start(); poll();
    return true;
  }
 private:
  void post(const QString& path, const QJsonObject& value, std::function<void(bool, QJsonObject)> done) {
    auto url = endpoint_; url.setPath(path);
    QNetworkRequest request(url);
    request.setSslConfiguration(tls_);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::ManualRedirectPolicy);
    request.setTransferTimeout(5000);
    request.setRawHeader("Authorization", "Bearer " + token_);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    auto* reply = network_.post(request, QJsonDocument(value).toJson(QJsonDocument::Compact));
    auto bytes = std::make_shared<QByteArray>();
    connect(reply, &QIODevice::readyRead, this, [reply, bytes] {
      bytes->append(reply->read(8193 - bytes->size()));
      if (bytes->size() > 8192) reply->abort();
    });
    connect(reply, &QNetworkReply::finished, this, [reply, bytes, done=std::move(done)] {
      bytes->append(reply->read(8193 - bytes->size()));
      QJsonParseError error;
      const auto doc = QJsonDocument::fromJson(*bytes, &error);
      const bool ok = reply->error() == QNetworkReply::NoError
          && reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200
          && bytes->size() <= 8192 && error.error == QJsonParseError::NoError && doc.isObject();
      reply->deleteLater(); done(ok, doc.object());
    });
  }
  bool consume(const QString& id) {
    consumed_.append(id);
    while (consumed_.size() > 128) consumed_.removeFirst();
    QSaveFile file(state_ + "/consumed.json");
    const auto bytes = QJsonDocument(consumed_).toJson(QJsonDocument::Compact);
    if (!file.open(QIODevice::WriteOnly) || !file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner)
        || file.write(bytes) != bytes.size() || !file.flush() || fsync(file.handle()) != 0 || !file.commit()) return false;
    const int directory = ::open(QFile::encodeName(state_).constData(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (directory < 0) return false;
    const bool ok = fsync(directory) == 0; ::close(directory); return ok;
  }
  void ack(const QString& id, const QString& result, std::function<void(bool)> done) {
    post("/v1/control/ack", {{"schema", 1}, {"boot_id", boot_}, {"command_id", id}, {"result", result}},
      [id, done=std::move(done)](bool ok, const QJsonObject& value) {
        done(ok && value["schema"].toInt() == 1 && value["accepted"].isBool() && value["accepted"].toBool()
             && value["command_id"].toString() == id);
      });
  }
  void execute(const QString& id, const QString& action) {
#ifdef ELO_CONTROL_TEST_EXECUTOR
    QFile output(state_ + "/executed");
    if (!output.open(QIODevice::WriteOnly | QIODevice::Append)) { ack(id, "failed", [](bool) {}); return; }
    output.write((id + " " + action + "\n").toUtf8()); output.close();
    qInfo("control: simulated system action");
#else
    auto* process = new QProcess(this);
    connect(process, &QProcess::errorOccurred, this, [this, id](QProcess::ProcessError) { ack(id, "failed", [](bool) {}); });
    connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
            [this, id, process](int code, QProcess::ExitStatus status) {
      if (code || status != QProcess::NormalExit) ack(id, "failed", [](bool) {});
      process->deleteLater();
    });
    process->start(action == "reboot" ? "/sbin/reboot" : "/sbin/poweroff", {});
#endif
  }
  void poll() {
    if (busy_) return;
    busy_ = true;
    auto age = std::make_shared<QElapsedTimer>(); age->start();
    QJsonObject report{{"schema", 1}, {"boot_id", boot_}};
    const auto tele = collectTelemetry();
    if (!tele.isEmpty()) report["telemetry"] = tele;
    post("/v1/control/poll", report, [this, age](bool ok, const QJsonObject& value) {
      if (!ok || value["schema"].toInt() != 1 || !value["command"].isObject()) { busy_ = false; return; }
      const auto command = value["command"].toObject();
      const auto id = command["id"].toString(), action = command["action"].toString();
      const int remaining = command["remaining_seconds"].toInt();
      if (!uuid(id) || (action != "reboot" && action != "poweroff") || command["state"].toString() != "pending"
          || command["boot_id"].toString() != boot_ || remaining < 1 || remaining > 120 || age->elapsed() >= remaining * 1000) {
        busy_ = false; return;
      }
      if (consumed_.contains(id)) { ack(id, "failed", [this](bool) { busy_ = false; }); return; }
      if (!consume(id)) { qCritical("control: cannot durably consume command; action refused"); busy_ = false; return; }
      ack(id, "accepted", [this, age, remaining, id, action](bool accepted) {
        if (!accepted || age->elapsed() + 1000 >= remaining * 1000) {
          ack(id, "failed", [this](bool) { busy_ = false; }); return;
        }
        QTimer::singleShot(1000, this, [this, id, action] { execute(id, action); busy_ = false; });
      });
    });
  }
  QString config_, state_, boot_;
  QLockFile lock_;
  QUrl endpoint_;
  QByteArray token_;
  QSslConfiguration tls_;
  QJsonArray consumed_;
  QNetworkAccessManager network_;
  QTimer timer_;
  bool busy_ = false;
};
}
int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  QCommandLineParser parser; parser.addHelpOption();
  parser.addOption({"config-dir", "Terminal configuration directory.", "directory", "/etc/elo-terminal"});
  parser.addOption({"state-dir", "Private durable command ledger directory.", "directory", "/var/lib/elo-control"});
  parser.process(app);
  Agent agent(parser.value("config-dir"), parser.value("state-dir"));
  if (!agent.start()) return 2;
  return app.exec();
}
