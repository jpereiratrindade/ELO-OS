// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include "QtAdapters.hpp"
#include <QCryptographicHash>
#include <QFile>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QTemporaryDir>
#include <QCoreApplication>
#include <QImage>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QQuickItem>
#include <QSignalSpy>
#include <QtTest>

class UiTest : public QObject {
  Q_OBJECT
 private slots:
  void runtimeHealthRequiresRenderedFrames() {
    struct Network : elo::NetworkStatus {
      bool up = true;
      bool available() const override { return up; }
    } network;
    BootClock clock;
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    const auto path = directory.path() + "/health";
    ClientModel model;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("clientModel", &model);
    engine.load(QUrl("qrc:/Main.qml"));
    QVERIFY(!engine.rootObjects().isEmpty());
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    QVERIFY(window);
    QtRuntime runtime(*window, model, clock, network, path, "qt-test-generation");
    runtime.start();
    QVERIFY(QTest::qWaitForWindowExposed(window));
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    auto record = [&path] {
      QFile file(path);
      if (!file.open(QIODevice::ReadOnly)) return QStringList{};
      return QString::fromUtf8(file.readAll()).simplified().split(' ');
    };
    QTRY_VERIFY(record().size() == 8);
    QCOMPARE(record()[0], "ELO_HEALTH_V1");
    QCOMPARE(record()[1], "qt-test-generation");
    QCOMPARE(record()[2], QString::number(QCoreApplication::applicationPid()));
    const auto sequence = record()[4].toULongLong();
    window->update();
    QTRY_VERIFY(record()[4].toULongLong() > sequence);
    const auto digest = model.presentationDigest();
    network.up = false;
    QTRY_COMPARE(model.state(), "DEGRADED_OFFLINE");
    QTRY_COMPARE(record()[5], "DEGRADED_OFFLINE");
    QCOMPARE(model.presentationDigest(), digest);
    network.up = true;
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    QTRY_COMPARE(record()[5], "READY_LOCAL");
  }
  void rejectedFixtureNeverBecomesReady() {
    struct MissingCatalog : elo::ContentCatalog {
      bool restored = false;
      elo::LoadResult load() override {
        return restored ? elo::LoadResult{elo::LoadStatus::loaded, elo::local_fixture()}
                        : elo::LoadResult{elo::LoadStatus::missing, {}};
      }
    } catalog;
    ClientModel model(nullptr, &catalog);
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("clientModel", &model);
    engine.load(QUrl("qrc:/Main.qml"));
    QCOMPARE(engine.rootObjects().size(), 1);
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    QVERIFY(window);
    QObject::connect(window, &QQuickWindow::frameSwapped, &model, &ClientModel::presentationReady, Qt::QueuedConnection);
    model.start();
    QVERIFY(QTest::qWaitForWindowExposed(window));
    QTest::qWait(100);
    QCOMPARE(model.state(), "ERROR_RECOVERABLE");
    QVERIFY(!model.error().isEmpty());
    QVERIFY(!model.canNext() && !model.canPrevious());
    auto* body = window->findChild<QObject*>("pageBody");
    QVERIFY(body);
    QCOMPARE(body->property("text").toString(), model.error());
    QVERIFY(model.canRetry());
    auto* retry = window->findChild<QQuickItem*>("resetButton");
    QVERIFY(retry);
    QCOMPARE(retry->property("label").toString(), "Tentar novamente");
    catalog.restored = true;
    model.retry();
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    QVERIFY(!model.canRetry());
  }
  void externalContentRequiresVerifiedBytes() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    QtLocalStore store(directory.path());
    JsonCatalog catalog(store);
    QCOMPARE(catalog.load().status, elo::LoadStatus::missing);
    const auto payload = QJsonDocument(QJsonObject{
      {"schema", 1}, {"id", "qt-store-test"}, {"name", "Fixture Qt"}, {"version", "1"},
      {"pages", QJsonArray{QJsonObject{{"title", "Local"}, {"body", "Teste sem servidor."}}}}
    }).toJson(QJsonDocument::Compact);
    const auto digest = QString::fromLatin1(QCryptographicHash::hash(payload, QCryptographicHash::Sha256).toHex());
    const auto bundle = directory.path() + "/bundles/" + digest;
    QVERIFY(QDir().mkpath(bundle));
    auto write = [](const QString& path, const QByteArray& data) {
      QFile file(path);
      return file.open(QIODevice::WriteOnly) && file.write(data) == data.size();
    };
    QVERIFY(write(bundle + "/presentation.json", payload));
    QVERIFY(write(bundle + "/manifest.json", QJsonDocument(QJsonObject{
      {"schema", 1}, {"file", "presentation.json"}, {"size", static_cast<int>(payload.size())}, {"sha256", digest}
    }).toJson()));
    QVERIFY(write(directory.path() + "/active.json", QJsonDocument(QJsonObject{{"bundle", digest}}).toJson()));
    ClientModel model(nullptr, &catalog);
    model.start();
    QCOMPARE(model.state(), "BOOTING");
    model.presentationReady();
    QCOMPARE(model.state(), "READY_LOCAL");
    QCOMPARE(model.title(), "Local");
    QVERIFY(write(bundle + "/presentation.json", payload.left(payload.size() - 1)));
    ClientModel corrupted(nullptr, &catalog);
    corrupted.start();
    corrupted.presentationReady();
    QCOMPARE(corrupted.state(), "ERROR_RECOVERABLE");
    QVERIFY(write(directory.path() + "/active.json", "{\"bundle\":\"../escape\"}"));
    QCOMPARE(store.read_active().status, elo::LoadStatus::invalid);
  }
  void localPresentation() {
    ClientModel model;
    QSignalSpy changes(&model, &ClientModel::changed);
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("clientModel", &model);
    engine.load(QUrl("qrc:/Main.qml"));
    QCOMPARE(engine.rootObjects().size(), 1);
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    QVERIFY(window);
    QObject::connect(window, &QQuickWindow::frameSwapped, &model, &ClientModel::presentationReady, Qt::QueuedConnection);
    QVERIFY(QTest::qWaitForWindowExposed(window));
    window->requestActivate();
    QVERIFY(QTest::qWaitForWindowActive(window));
    model.start();
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    QVERIFY(changes.size() >= 2);
    QVERIFY(model.fixtureLabel().contains("fixture v1"));
    auto* title = window->findChild<QObject*>("pageTitle");
    auto* counter = window->findChild<QObject*>("pageCounter");
    QVERIFY(title && counter);
    const auto first = title->property("text").toString();
    QVERIFY(!first.isEmpty());
    QTest::keyClick(window, Qt::Key_Right);
    QTRY_COMPARE(model.pageNumber(), 2);
    const auto before_network = model.presentationDigest();
    model.setNetworkAvailable(true);
    model.setNetworkAvailable(false);
    QCOMPARE(model.state(), "DEGRADED_OFFLINE");
    QCOMPARE(model.presentationDigest(), before_network);
    QCOMPARE(model.pageNumber(), 2);
    model.setNetworkAvailable(true);
    QCOMPARE(model.state(), "READY_LOCAL");
    QVERIFY(model.connectivity().contains("servidor não verificado"));
    QTRY_COMPARE(counter->property("text").toString(), "2 / 3");
    QVERIFY(title->property("text").toString() != first);
    QTest::keyClick(window, Qt::Key_Left);
    QTRY_COMPARE(model.pageNumber(), 1);
    auto* next = window->findChild<QQuickItem*>("nextButton");
    auto* reset = window->findChild<QQuickItem*>("resetButton");
    QVERIFY(next && reset);
    QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                     next->mapToScene(QPointF(next->width()/2, next->height()/2)).toPoint());
    QTRY_COMPARE(model.pageNumber(), 2);
    QTest::keyClick(window, Qt::Key_Space);
    QTRY_COMPARE(model.pageNumber(), 3);
    QVERIFY(!model.canNext());
    QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                     reset->mapToScene(QPointF(reset->width()/2, reset->height()/2)).toPoint());
    QTRY_COMPARE(model.pageNumber(), 1);
    QTest::keyClick(window, Qt::Key_Right);
    QTest::keyClick(window, Qt::Key_Home);
    QTRY_COMPARE(title->property("text").toString(), first);
    QTRY_COMPARE(model.pageNumber(), 1);
    QTest::qWait(200);
    const auto frame = window->grabWindow();
    QVERIFY(!frame.isNull());
    QCOMPARE(frame.size(), window->size() * window->devicePixelRatio());
    bool painted = false;
    for (int y = 0; y < frame.height(); y += 8)
      for (int x = 0; x < frame.width(); x += 8)
        painted |= frame.pixelColor(x, y) != QColor("#101d23");
    QVERIFY(painted);
    const auto screenshot = qEnvironmentVariable("ELO_SCREENSHOT");
    if (!screenshot.isEmpty()) QVERIFY(frame.save(screenshot));
  }
};
QTEST_MAIN(UiTest)
#include "ui-test.moc"
