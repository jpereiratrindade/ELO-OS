// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
#include "QtAdapters.hpp"
#include <QCryptographicHash>
#include <QFile>
#include <QSaveFile>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QTemporaryDir>
#include <QCoreApplication>
#include <QImage>
#include <QBuffer>
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
  void liveContentWaitsForSessionBoundary() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    QtLocalStore store(directory.path());
    JsonCatalog catalog(store);
    auto publish = [&directory](const QString& title) {
      const auto payload = QJsonDocument(QJsonObject{
        {"schema", 1}, {"id", "live-elo"}, {"name", "Publicação ELO"}, {"version", "1"},
        {"pages", QJsonArray{QJsonObject{{"title", title}, {"body", "Publicação local."}},
                            QJsonObject{{"title", "Segunda página"}, {"body", "Sessão em andamento."}}}}
      }).toJson();
      const auto digest = QString::fromLatin1(QCryptographicHash::hash(payload, QCryptographicHash::Sha256).toHex());
      const auto bundle = directory.path() + "/bundles/" + digest;
      if (!QDir().mkpath(bundle)) return false;
      auto write = [](const QString& path, const QByteArray& bytes) {
        QSaveFile file(path);
        return file.open(QIODevice::WriteOnly) && file.write(bytes) == bytes.size() && file.commit();
      };
      return write(bundle + "/presentation.json", payload)
          && write(bundle + "/manifest.json", QJsonDocument(QJsonObject{
            {"schema", 1}, {"file", "presentation.json"}, {"size", static_cast<int>(payload.size())}, {"sha256", digest}
          }).toJson())
          && write(directory.path() + "/active.json", QJsonDocument(QJsonObject{{"bundle", digest}}).toJson());
    };
    QVERIFY(publish("Primeira publicação"));
    struct Network : elo::NetworkStatus {
      bool available() const override { return false; }
    } network;
    BootClock clock;
    ClientModel model(nullptr, &catalog);
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("clientModel", &model);
    engine.load(QUrl("qrc:/Main.qml"));
    QVERIFY(!engine.rootObjects().isEmpty());
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    QVERIFY(window);
    QtRuntime runtime(*window, model, clock, network, directory.path() + "/health", "live-content-test");
    runtime.start();
    QVERIFY(QTest::qWaitForWindowExposed(window));
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    model.next();
    const auto old_digest = model.presentationDigest();
    const auto old_title = model.title();
    QVERIFY(publish("Novo conteúdo ELO"));
    // Exercise the actual runtime timer, not a direct call to the model seam.
    QTRY_VERIFY_WITH_TIMEOUT(!model.contentUpdate().isEmpty(), 5000);
    QCOMPARE(model.presentationDigest(), old_digest);
    QCOMPARE(model.title(), old_title);
    QCOMPARE(model.pageNumber(), 2);
    auto* reset = window->findChild<QQuickItem*>("resetButton");
    QVERIFY(reset);
    QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                      reset->mapToScene(QPointF(reset->width() / 2, reset->height() / 2)).toPoint());
    QTRY_COMPARE(model.title(), "Novo conteúdo ELO");
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    QCOMPARE(model.pageNumber(), 1);
    QVERIFY(model.contentUpdate().isEmpty());
    QVERIFY(model.presentationDigest() != old_digest);
    auto* title = window->findChild<QObject*>("pageTitle");
    QVERIFY(title);
    QTRY_COMPARE(title->property("text").toString(), "Novo conteúdo ELO");
    const auto new_digest = model.presentationDigest();
    QFile pointer(directory.path() + "/active.json");
    QVERIFY(pointer.open(QIODevice::WriteOnly | QIODevice::Truncate));
    QCOMPARE(pointer.write("invalid"), qint64(7));
    pointer.close();
    QTRY_VERIFY_WITH_TIMEOUT(model.contentUpdate().contains("preservado"), 5000);
    model.reset();
    QCOMPARE(model.presentationDigest(), new_digest);
    QCOMPARE(model.state(), "READY_LOCAL");
    QVERIFY(model.error().isEmpty());
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
    model.checkContent();
    QVERIFY(model.contentUpdate().contains("preservado"));
    QCOMPARE(model.title(), "Local");
    model.reset();
    QCOMPARE(model.state(), "READY_LOCAL");
    QCOMPARE(model.title(), "Local");
    ClientModel corrupted(nullptr, &catalog);
    corrupted.start();
    corrupted.presentationReady();
    QCOMPARE(corrupted.state(), "ERROR_RECOVERABLE");
    QVERIFY(write(directory.path() + "/active.json", "{\"bundle\":\"../escape\"}"));
    QCOMPARE(store.read_active().status, elo::LoadStatus::invalid);
  }
  void imagePresentationRequiresValidatedPixels() {
    struct MemoryStore : elo::LocalStore {
      QByteArray bytes;
      elo::StoredContent read_active() const override { return {elo::LoadStatus::loaded, bytes.toStdString()}; }
    } store;
    auto imageDocument = [](int width) {
      QImage image(width, 16, QImage::Format_RGB32);
      image.fill(QColor("#ea2739"));
      QByteArray raw;
      QBuffer buffer(&raw);
      buffer.open(QIODevice::WriteOnly);
      image.save(&buffer, "PNG");
      return QJsonObject{{"mime", "image/png"}, {"base64", QString::fromLatin1(raw.toBase64())},
          {"sha256", QString::fromLatin1(QCryptographicHash::hash(raw, QCryptographicHash::Sha256).toHex())},
          {"alt", "Imagem de teste vermelha"}};
    };
    QJsonObject page{{"title", "Imagem local"}, {"body", "Disponível sem rede."}, {"image", imageDocument(16)}};
    QJsonObject document{{"schema", 1}, {"id", "image-test"}, {"name", "Imagem"}, {"version", "2"},
                         {"pages", QJsonArray{page}}};
    store.bytes = QJsonDocument(document).toJson();
    JsonCatalog catalog(store);
    QCOMPARE(catalog.load().status, elo::LoadStatus::loaded);
    ClientModel model(nullptr, &catalog);
    QSignalSpy receipts(&model, &ClientModel::contentPresented);
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("clientModel", &model);
    engine.load(QUrl("qrc:/Main.qml"));
    QVERIFY(!engine.rootObjects().isEmpty());
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    QVERIFY(window);
    struct Network : elo::NetworkStatus { bool available() const override { return false; } } network;
    BootClock clock;
    QtRuntime runtime(*window, model, clock, network);
    runtime.start();
    QVERIFY(QTest::qWaitForWindowExposed(window));
    QTRY_COMPARE(model.state(), "READY_LOCAL");
    auto* item = window->findChild<QQuickItem*>("pageImage");
    QVERIFY(item && item->isVisible());
    QCOMPARE(item->property("status").toInt(), 1);
    QCOMPARE(model.imageAlt(), "Imagem de teste vermelha");
    QTRY_VERIFY(!receipts.empty());
    QCOMPARE(receipts.last()[0].toByteArray(), model.contentDigest());
    const auto pixel = item->mapToScene(QPointF(item->width()/2, item->height()/2)).toPoint();
    const auto frame = window->grabWindow();
    QVERIFY(!frame.isNull());
    QVERIFY(frame.pixelColor(pixel).red() > 200 && frame.pixelColor(pixel).green() < 80);
    const auto realRoot = qEnvironmentVariable("ELO_IMAGE_CONTENT_DIR");
    if (!realRoot.isEmpty()) {
      QtLocalStore realStore(realRoot);
      const auto stored = realStore.read_active();
      QCOMPARE(stored.status, elo::LoadStatus::loaded);
      store.bytes = QByteArray::fromStdString(stored.utf8);
      model.checkContent(); model.reset();
      QTRY_COMPARE(model.state(), "READY_LOCAL");
      QTRY_COMPARE(item->property("status").toInt(), 1);
      QTest::qWait(100);
      const auto target = qEnvironmentVariable("ELO_IMAGE_SCREENSHOT");
      if (!target.isEmpty()) QVERIFY(window->grabWindow().save(target));
    }
    const auto digest = model.contentDigest();
    page["image"] = imageDocument(4097);
    document["pages"] = QJsonArray{page};
    store.bytes = QJsonDocument(document).toJson();
    QCOMPARE(catalog.load().status, elo::LoadStatus::invalid);
    model.checkContent(); model.reset();
    QCOMPARE(model.contentDigest(), digest);
    QVERIFY(model.contentUpdate().contains("preservado"));
    page["image"] = imageDocument(16);
    auto corrupted = page["image"].toObject(); corrupted["sha256"] = QString(64, QLatin1Char('0'));
    page["image"] = corrupted; document["pages"] = QJsonArray{page};
    store.bytes = QJsonDocument(document).toJson();
    QCOMPARE(catalog.load().status, elo::LoadStatus::invalid);
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
    QVERIFY(model.fixtureLabel().contains("formato local v1"));
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
        painted |= frame.pixelColor(x, y) != window->color();
    QVERIFY(painted);
    const auto screenshot = qEnvironmentVariable("ELO_SCREENSHOT");
    if (!screenshot.isEmpty()) QVERIFY(frame.save(screenshot));
  }
};
QTEST_MAIN(UiTest)
#include "ui-test.moc"
