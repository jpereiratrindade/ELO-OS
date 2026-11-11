// SPDX-License-Identifier: GPL-3.0-only
#include "MediaSurface.hpp"
#include "QtAdapters.hpp"
#include <QBuffer>
#include <QDataStream>
#include <QFile>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QProcess>
#include <QQuickWindow>
#include <QTemporaryDir>
#include <QtTest>
class MediaTest : public QObject {
  Q_OBJECT
 private slots:
  void audioValidationDecodeAndPause() {
    QTemporaryDir dir;
    QByteArray bytes; QDataStream wav(&bytes, QIODevice::WriteOnly); wav.setByteOrder(QDataStream::LittleEndian);
    wav.writeRawData("RIFF", 4); wav << quint32(36 + 64000); wav.writeRawData("WAVEfmt ", 8);
    wav << quint32(16) << quint16(1) << quint16(1) << quint32(16000) << quint32(32000) << quint16(2) << quint16(16);
    wav.writeRawData("data", 4); wav << quint32(64000); bytes.append(QByteArray(64000, '\0'));
    QJsonObject media{{"kind", "audio"}, {"mime", "audio/wav"},
      {"sha256", QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex())},
      {"base64", QString::fromLatin1(bytes.toBase64())}};
    QJsonObject page{{"title", "Áudio"}, {"body", "Apresentação offline"}, {"media", media}};
    QJsonObject data{{"schema", 1}, {"id", "av"}, {"name", "Teste"}, {"version", "5"}, {"pages", QJsonArray{page}}};
    struct Store : elo::LocalStore {
      QByteArray data;
      elo::StoredContent read_active() const override { return {elo::LoadStatus::loaded, data.toStdString()}; }
    } store;
    store.data = QJsonDocument(data).toJson(); JsonCatalog catalog(store); auto loaded = catalog.load();
    QCOMPARE(loaded.status, elo::LoadStatus::loaded); QCOMPARE(loaded.fixture.pages[0].media_kind, std::string("audio"));
    const QUrl source(QString::fromStdString(loaded.fixture.pages[0].media_source));
    QVERIFY(source.isLocalFile()); QFile file(source.toLocalFile()); QVERIFY(file.open(QIODevice::ReadOnly)); QCOMPARE(file.readAll(), bytes);
    MediaSurface surface; surface.setKind("audio"); surface.setSource(source);
    QTRY_VERIFY_WITH_TIMEOUT(surface.ready(), 5000); QVERIFY2(surface.error().isEmpty(), qPrintable(surface.error()));
    QTRY_VERIFY_WITH_TIMEOUT(surface.position() > 100, 5000);
    surface.setActive(false); auto position = surface.position(); QTest::qWait(250); QVERIFY(qAbs(surface.position() - position) < 100);
    surface.setActive(true); QTRY_VERIFY(surface.position() > position);
    media["sha256"] = QString(64, '0'); page["media"] = media; data["pages"] = QJsonArray{page}; store.data = QJsonDocument(data).toJson();
    QCOMPARE(catalog.load().status, elo::LoadStatus::invalid);
  }
  void lateDurationExtendsExposureInsteadOfCuttingMedia() {
    struct Catalog : elo::ContentCatalog {
      elo::LoadResult load() override {
        elo::Fixture fixture{"timer", "Media timing", "5", {{"First", "Audio"}, {"Second", "Next page"}}};
        fixture.pages[0].media_source = "file:///local-test.wav";
        fixture.pages[0].media_kind = "audio"; fixture.pages[0].media_hash = std::string(64, 'a');
        fixture.content_hash = std::string(64, 'b'); fixture.exposure_seconds = 5;
        return {elo::LoadStatus::loaded, fixture};
      }
    } catalog;
    ClientModel model(nullptr, &catalog); model.start(); model.presentationReady();
    model.confirmPresented(model.contentDigest()); model.setMediaDuration(7000);
    QTest::qWait(5300); QCOMPARE(model.pageNumber(), 1);
    QTRY_COMPARE_WITH_TIMEOUT(model.pageNumber(), 2, 2500);
  }
  void videoProducesPixelsAndCanRestart() {
    QTemporaryDir dir; const auto path = dir.filePath("blue.webm");
    QProcess ffmpeg; ffmpeg.start("ffmpeg", {"-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=10:d=2", "-c:v", "libvpx", "-an", "-y", path});
    QVERIFY(ffmpeg.waitForFinished(15000)); QVERIFY2(ffmpeg.exitCode() == 0, ffmpeg.readAllStandardError().constData());
    QQuickWindow window; window.resize(320, 180); window.setColor(Qt::black);
    MediaSurface surface(window.contentItem()); surface.setSize(QSizeF(320, 180)); surface.setKind("video");
    window.show(); surface.setSource(QUrl::fromLocalFile(path));
    QTRY_VERIFY_WITH_TIMEOUT(surface.ready(), 5000); QVERIFY2(surface.error().isEmpty(), qPrintable(surface.error()));
    QTest::qWait(200); auto image = window.grabWindow(); QVERIFY(!image.isNull());
    auto pixel = image.pixelColor(image.width() / 2, image.height() / 2); QVERIFY(pixel.blue() > 180 && pixel.red() < 60);
    surface.setActive(false); auto position = surface.position(); QTest::qWait(200); QVERIFY(qAbs(surface.position() - position) < 100);
    surface.restart(); QTRY_VERIFY(surface.ready()); surface.setActive(true); QTRY_VERIFY(surface.position() > 0);
  }
};
QTEST_MAIN(MediaTest)
#include "media-test.moc"
