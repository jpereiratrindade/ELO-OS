// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QUrl>

int main(int argc, char* argv[]) {
  QGuiApplication app(argc, argv);
  QGuiApplication::setApplicationName("elo-client");
  ClientModel model;
  QQmlApplicationEngine engine;
  engine.rootContext()->setContextProperty("clientModel", &model);
  engine.load(QUrl(QStringLiteral("qrc:/Main.qml")));
  if (engine.rootObjects().isEmpty()) return 2;
  auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
  if (!window) return 2;
  QObject::connect(window, &QQuickWindow::frameSwapped, &model, &ClientModel::presentationReady, Qt::QueuedConnection);
  model.start();
  if (app.arguments().contains("--fullscreen")) {
    window->showFullScreen();
  }
  return app.exec();
}
