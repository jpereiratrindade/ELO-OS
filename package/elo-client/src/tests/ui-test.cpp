// SPDX-License-Identifier: GPL-3.0-only
#include "ClientModel.hpp"
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
  void rejectedFixtureNeverBecomesReady() {
    struct MissingCatalog : elo::ContentCatalog {
      elo::LoadResult load() override { return {elo::LoadStatus::missing, {}}; }
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
