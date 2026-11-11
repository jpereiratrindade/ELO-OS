// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <QObject>
#include <QVector>
#include <QJsonArray>
#include <memory>
namespace elo::perception { class VisionService; }
class PerceptionModel : public QObject {
  Q_OBJECT
  Q_PROPERTY(QString status READ status NOTIFY changed)
  Q_PROPERTY(bool operational READ operational NOTIFY changed)
  Q_PROPERTY(bool attention READ attention NOTIFY changed)
  Q_PROPERTY(bool authorized READ authorized NOTIFY changed)
  Q_PROPERTY(bool recognitionAvailable READ recognitionAvailable NOTIFY changed)
  Q_PROPERTY(bool canEnroll READ canEnroll NOTIFY changed)
  Q_PROPERTY(bool hasProfile READ hasProfile NOTIFY changed)
  Q_PROPERTY(bool hasCandidate READ hasCandidate NOTIFY changed)
  Q_PROPERTY(int resumePage READ resumePage NOTIFY changed)
 public:
  PerceptionModel(QString camera, QString detector, QString recognizer, QString gallery, QObject* parent = nullptr);
  ~PerceptionModel() override;
  void start();
  QString status() const { return status_; }
  quint64 processedFrames() const { return processed_frames_; }
  bool operational() const { return operational_; }
  bool attention() const { return attention_; }
  bool authorized() const { return authorized_; }
  bool recognitionAvailable() const { return !gallery_.isEmpty() && !model_hash_.isEmpty() && gallery_valid_; }
  bool canEnroll() const { return authorized_ && !query_.isEmpty() && identity_.isEmpty() && candidate_.isEmpty() && !uncertain_; }
  bool hasProfile() const { return !identity_.isEmpty(); }
  bool hasCandidate() const { return !candidate_.isEmpty(); }
  int resumePage() const;
  void presentation(QString digest, int page);
  Q_INVOKABLE void setAuthorized(bool authorized);
  Q_INVOKABLE void enroll();
  Q_INVOKABLE void confirmIdentity();
  Q_INVOKABLE void forget();
  // Transient embeddings from the camera adapter; also permits deterministic adapter tests.
  void observeEmbedding(const QVector<float>& embedding, double quality);
 signals:
  void changed();
 private:
  bool save();
  void load();
  QString camera_, detector_, recognizer_, gallery_, model_hash_;
  QString status_ = "Câmera desligada · experiência disponível sem reconhecimento";
  QString identity_, candidate_, publication_;
  int page_ = 1;
  bool operational_ = false, attention_ = false, authorized_ = false, gallery_valid_ = true, uncertain_ = false;
  quint64 processed_frames_ = 0;
  QVector<float> query_;
  QJsonArray profiles_;
  std::unique_ptr<elo::perception::VisionService> service_;
};
