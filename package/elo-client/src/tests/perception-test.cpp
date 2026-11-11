// SPDX-License-Identifier: GPL-3.0-only
#include "perception/PerceptionModel.hpp"
#include <QTemporaryDir>
#include <QFile>
#include <QtTest>
class PerceptionTest : public QObject {
  Q_OBJECT
 private slots:
  void consentPersistenceAmbiguityAndErasure() {
    QTemporaryDir dir; QVERIFY(dir.isValid());
    const auto modelPath = dir.filePath("model.onnx");
    QFile model(modelPath); QVERIFY(model.open(QIODevice::WriteOnly)); model.write("model-identity-fixture"); model.close();
    const auto gallery = dir.filePath("private/visits.json");
    QVector<float> first(128, 0); first[0] = 1;
    PerceptionModel perception({}, {}, modelPath, gallery);
    QVERIFY(perception.recognitionAvailable());
    perception.observeEmbedding(first, 1);
    QVERIFY(!perception.canEnroll()); QVERIFY(!QFile::exists(gallery));
    perception.setAuthorized(true); perception.observeEmbedding(first, 0.5); QVERIFY(!perception.canEnroll());
    perception.observeEmbedding(first, 1); QVERIFY(perception.canEnroll());
    perception.presentation("publication-a", 2); perception.enroll(); QVERIFY(perception.hasProfile());
    QVERIFY(QFile::exists(gallery));
    QVERIFY(!(QFile::permissions(gallery) & (QFileDevice::ReadGroup | QFileDevice::ReadOther)));
    perception.presentation("publication-a", 3);
    PerceptionModel restart({}, {}, modelPath, gallery);
    restart.presentation("publication-a", 1); restart.setAuthorized(true); restart.observeEmbedding(first, 1);
    QVERIFY(restart.hasCandidate()); QVERIFY(!restart.hasProfile()); QCOMPARE(restart.resumePage(), 3);
    restart.confirmIdentity(); QVERIFY(restart.hasProfile());
    restart.forget(); QVERIFY(!restart.hasProfile()); QVERIFY(!restart.authorized());
    PerceptionModel erased({}, {}, modelPath, gallery); erased.setAuthorized(true); erased.observeEmbedding(first, 1);
    QVERIFY(!erased.hasCandidate()); QVERIFY(erased.canEnroll());
  }
  void ambiguousMatchesNeverResumeOrEnroll() {
    QTemporaryDir dir; QFile model(dir.filePath("model")); QVERIFY(model.open(QIODevice::WriteOnly)); model.write("model-fixture"); model.close();
    PerceptionModel p({}, {}, model.fileName(), dir.filePath("private/gallery.json"));
    QVector<float> first(128, 0); first[0] = 1;
    QVector<float> second(128, 0); second[1] = 1;
    p.setAuthorized(true); p.observeEmbedding(first, 1); p.enroll(); QVERIFY(p.hasProfile());
    p.setAuthorized(true); p.observeEmbedding(second, 1); p.enroll(); QVERIFY(p.hasProfile());
    QVector<float> ambiguous(128, 0); ambiguous[0] = ambiguous[1] = 0.7071F;
    p.setAuthorized(true); p.observeEmbedding(ambiguous, 1);
    QVERIFY(!p.hasCandidate()); QVERIFY(!p.hasProfile()); QVERIFY(!p.canEnroll()); QCOMPARE(p.resumePage(), 0);
  }
  void cameraHardwareOptInSmoke() {
    const auto device = qEnvironmentVariable("ELO_TEST_CAMERA");
    if (device.isEmpty()) QSKIP("Hardware capture requires explicit ELO_TEST_CAMERA and ELO_TEST_DETECTOR");
    PerceptionModel p(device, qEnvironmentVariable("ELO_TEST_DETECTOR"), {}, {});
    p.start(); QTRY_VERIFY_WITH_TIMEOUT(p.operational(), 10000);
    QTRY_VERIFY_WITH_TIMEOUT(p.processedFrames() >= 3, 10000); QVERIFY(p.operational()); QVERIFY(!p.authorized()); QVERIFY(!p.recognitionAvailable());
  }
  void invalidStoreNeverEnablesRecognition() {
    QTemporaryDir dir;
    QFile model(dir.filePath("model")); QVERIFY(model.open(QIODevice::WriteOnly)); model.write("model"); model.close();
    QFile gallery(dir.filePath("gallery")); QVERIFY(gallery.open(QIODevice::WriteOnly)); gallery.write("not-json"); gallery.close();
    PerceptionModel p({}, {}, model.fileName(), gallery.fileName());
    QVERIFY(!p.recognitionAvailable()); p.setAuthorized(true); QVERIFY(!p.authorized());
  }
};
QTEST_GUILESS_MAIN(PerceptionTest)
#include "perception-test.moc"
