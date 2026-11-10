// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include "QtAdapters.hpp"
#include "ContentSync.hpp"
#include <memory>
#include <QCommandLineParser>
#include <QDir>
#include <QDebug>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QtQml/qtqml-config.h>
#include <QQuickWindow>
#include <QUrl>
#include <QRegularExpression>
#include <QShortcut>
#include <QCursor>
#include <QKeySequence>

static_assert(QT_FEATURE_qml_network == 1,
              "ELO requires Qt QML network support to present embedded image URLs");

int main(int argc, char* argv[]) {
  QGuiApplication app(argc, argv);
  QGuiApplication::setApplicationName("elo-client");
  QCommandLineParser parser;
  parser.addHelpOption();
  parser.addOption({"fullscreen", "Present in fullscreen."});
  parser.addOption({"exit-on-escape", "Allow Escape to quit a local bench session."});
  parser.addOption({"content-dir", "Read explicitly activated local content.", "directory"});
  parser.addOption({"health-file", "Publish local presentation health for the supervisor.", "file"});
  parser.addOption({"health-token", "Supervisor generation identifier, not an authentication credential.", "token"});
  parser.addOption({"server", "Distribution URL ending in /v1/presentation (HTTPS).", "url"});
  parser.addOption({"token-file", "Private individual terminal bearer token file.", "file"});
  parser.addOption({"ca-file", "Trust this CA bundle for the distribution server.", "file"});
  parser.addOption({"allow-loopback-http", "Explicit HTTP development on literal 127.0.0.1 only."});
  parser.process(app);
  if ((parser.isSet("server") && (!parser.isSet("content-dir") || !parser.isSet("token-file")))
      || (!parser.isSet("server") && (parser.isSet("token-file") || parser.isSet("ca-file") || parser.isSet("allow-loopback-http")))) {
    qCritical() << "Distribution requires --server, --content-dir and --token-file together";
    return 2;
  }
  const auto health_file = parser.value("health-file");
  const auto token = parser.value("health-token");
  if (parser.isSet("content-dir") && parser.value("content-dir").isEmpty()) return 2;
  if ((parser.isSet("health-file") || parser.isSet("health-token")) &&
      (!QDir::isAbsolutePath(health_file) || !QRegularExpression("^[A-Za-z0-9-]{1,64}$").match(token).hasMatch())) {
    qCritical() << "Invalid health file/token pair";
    return 2;
  }
  QtLocalStore store(parser.value("content-dir"));
  JsonCatalog catalog(store);
  QtDiagnostics diagnostics;
  ClientModel model(nullptr, parser.isSet("content-dir") ? &catalog : nullptr, &diagnostics);
  bool cursor_hidden = false;
  QObject::connect(&model, &ClientModel::changed, &app, [&model, &cursor_hidden] {
    if (model.autoplay() == cursor_hidden) return;
    cursor_hidden = model.autoplay();
    if (cursor_hidden) QGuiApplication::setOverrideCursor(QCursor(Qt::BlankCursor));
    else QGuiApplication::restoreOverrideCursor();
  });
  std::unique_ptr<ContentSync> sync;
  if (parser.isSet("server")) {
    sync = std::make_unique<ContentSync>(model, parser.value("content-dir"), QUrl(parser.value("server")),
        parser.value("token-file"), parser.value("ca-file"), parser.isSet("allow-loopback-http"));
    const auto error = sync->configure();
    if (!error.isEmpty()) { qCritical().noquote() << error; return 2; }
  }
  QQmlApplicationEngine engine;
  engine.rootContext()->setContextProperty("clientModel", &model);
  engine.load(QUrl(QStringLiteral("qrc:/Main.qml")));
  if (engine.rootObjects().isEmpty()) return 2;
  auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
  if (!window) return 2;
  if (parser.isSet("exit-on-escape")) {
    auto* exitShortcut = new QShortcut(QKeySequence(Qt::Key_Escape), window);
    QObject::connect(exitShortcut, &QShortcut::activated, &app, &QCoreApplication::quit);
  }
  BootClock clock;
  LinuxNetworkStatus network;
  QtRuntime runtime(*window, model, clock, network, health_file, token);
  bool sync_started = false;
  if (sync) {
    QObject::connect(window, &QQuickWindow::frameSwapped, &app, [&sync, &sync_started] {
      if (!sync_started) { sync_started = true; sync->start(); }
    }, Qt::QueuedConnection);
  }
  runtime.start();
  if (parser.isSet("fullscreen")) {
    window->showFullScreen();
  }
  return app.exec();
}
