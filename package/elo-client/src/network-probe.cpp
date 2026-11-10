// SPDX-License-Identifier: GPL-3.0-only
#include <QCoreApplication>
#include <QCommandLineParser>
#include <QFile>
#include <QFileInfo>
#include <QNetworkAccessManager>
#include <QNetworkProxy>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslError>
#include <QSslSocket>
#include <QTimer>
#include <QTextStream>
#include <QUrl>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  QCommandLineParser parser;
  parser.addHelpOption();
  parser.addOption({"server", "HTTPS presentation URL", "url"});
  parser.addOption({"token-file", "Private terminal credential file", "path"});
  parser.addOption({"ca-file", "Explicit trusted CA", "path"});
  parser.process(app);
  QTextStream out(stdout);
  const QUrl endpoint(parser.value("server"));
  if (!endpoint.isValid() || endpoint.scheme() != "https" || endpoint.host().isEmpty()
      || !endpoint.userInfo().isEmpty() || endpoint.hasQuery() || endpoint.hasFragment()
      || endpoint.path() != "/v1/presentation") { out << "CONFIG: servidor HTTPS inválido\n"; return 2; }
  const auto path = QFile::encodeName(parser.value("token-file"));
  const int descriptor = ::open(path.constData(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
  struct stat info{};
  if (descriptor < 0) { out << "CREDENTIAL: arquivo inacessível\n"; return 2; }
  QFile file;
  const bool valid = !::fstat(descriptor, &info) && S_ISREG(info.st_mode) && !(info.st_mode & 0077)
      && file.open(descriptor, QIODevice::ReadOnly);
  auto token = valid ? file.read(257).trimmed() : QByteArray{};
  file.close(); ::close(descriptor);
  if (!QRegularExpression("^[A-Za-z0-9_-]{32,128}$").match(QString::fromLatin1(token)).hasMatch()) {
    out << "CREDENTIAL: arquivo inválido ou permissões devem ser 0600\n"; return 2;
  }
  auto tls = QSslConfiguration::defaultConfiguration();
  tls.setPeerVerifyMode(QSslSocket::VerifyPeer);
  tls.setProtocol(QSsl::TlsV1_2OrLater);
  if (parser.isSet("ca-file")) {
    QFile ca(parser.value("ca-file"));
    if (!ca.open(QIODevice::ReadOnly) || ca.size() > 262144) { out << "CA: arquivo inválido\n"; return 2; }
    const auto certificates = QSslCertificate::fromData(ca.readAll());
    if (certificates.isEmpty()) { out << "CA: certificado inválido\n"; return 2; }
    tls.setCaCertificates(certificates);
  }
  QNetworkAccessManager manager;
  manager.setProxy(QNetworkProxy::NoProxy);
  QNetworkRequest request(endpoint);
  request.setSslConfiguration(tls);
  request.setRawHeader("Authorization", "Bearer " + token);
  request.setRawHeader("X-ELO-Capabilities", "text-v1,image-v2,reveal-v3,autoplay-v4");
  request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::ManualRedirectPolicy);
  auto* reply = manager.get(request);
  reply->setReadBufferSize(65536);
  qint64 received = 0;
  QObject::connect(reply, &QNetworkReply::readyRead, &app, [&] {
    received += reply->readAll().size();
    if (received > 16 * 1024 * 1024) reply->abort();
  });
  QObject::connect(reply, &QNetworkReply::sslErrors, &app, [&](const QList<QSslError>& errors) {
    for (const auto& error : errors) out << "TLS: " << error.errorString() << '\n';
    out.flush(); // Verification remains enabled; never ignore SSL errors.
  });
  QObject::connect(reply, &QNetworkReply::finished, &app, [&] {
    const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    out << "HTTP: " << status << " · rede: " << int(reply->error()) << '\n';
    if (reply->error() != QNetworkReply::NoError) out << "ERROR: " << reply->errorString() << '\n';
    out.flush();
    app.exit(status == 200 && reply->error() == QNetworkReply::NoError ? 0 : 1);
  });
  QTimer::singleShot(15000, reply, &QNetworkReply::abort);
  return app.exec();
}
