// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include "QtAdapters.hpp"
#include <QCommandLineParser>
#include <QDir>
#include <QDebug>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QUrl>
#include <QRegularExpression>
#include <QShortcut>
#include <QKeySequence>

int main(int argc, char* argv[]) {
  QGuiApplication app(argc, argv);
  QGuiApplication::setApplicationName("elo-client");
  QCommandLineParser parser;
  parser.addHelpOption();
  parser.addOption({"fullscreen", "Present in fullscreen."});
  parser.addOption({"exit-on-escape", "Allow Escape to quit a local bench session."});
  parser.addOption({"content-dir", "Read an explicitly activated local test fixture.", "directory"});
  parser.addOption({"health-file", "Publish local presentation health for the supervisor.", "file"});
  parser.addOption({"health-token", "Supervisor generation identifier, not an authentication credential.", "token"});
  parser.process(app);
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
  runtime.start();
  if (parser.isSet("fullscreen")) {
    window->showFullScreen();
  }
  return app.exec();
}
