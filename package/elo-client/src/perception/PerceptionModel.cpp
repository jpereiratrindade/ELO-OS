// SPDX-License-Identifier: GPL-3.0-only
#include "PerceptionModel.hpp"
#include "VisionService.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QUuid>
#include <QTimer>
#include <algorithm>
#include <cmath>
namespace {
constexpr int dimensions = 128;
bool valid(const QVector<float>& values) {
  double norm = 0;
  if (values.size() != dimensions) return false;
  for (auto value : values) { if (!std::isfinite(value)) return false; norm += double(value) * value; }
  return norm > 1e-12;
}
double similarity(const QVector<float>& a, const QJsonArray& b) {
  if (b.size() != a.size()) return -1;
  double dot = 0, norm_a = 0, norm_b = 0;
  for (int i = 0; i < a.size(); ++i) {
    const auto v = b[i].toDouble(); dot += a[i] * v; norm_a += double(a[i]) * a[i]; norm_b += v * v;
  }
  return norm_a > 0 && norm_b > 0 ? dot / std::sqrt(norm_a * norm_b) : -1;
}
}
PerceptionModel::PerceptionModel(QString camera, QString detector, QString recognizer, QString gallery, QObject* parent)
    : QObject(parent), camera_(std::move(camera)), detector_(std::move(detector)), recognizer_(std::move(recognizer)), gallery_(std::move(gallery)) {
  QFile model(recognizer_);
  if (!recognizer_.isEmpty() && model.open(QIODevice::ReadOnly)) {
    QCryptographicHash hash(QCryptographicHash::Sha256); hash.addData(&model); model_hash_ = QString::fromLatin1(hash.result().toHex());
  }
  load();
}
PerceptionModel::~PerceptionModel() = default;
void PerceptionModel::start() {
  if (camera_.isEmpty() || service_) return;
  if (!QFileInfo(detector_).isFile()) { status_ = "Detector ausente · reprodução mantida sem câmera"; emit changed(); return; }
  elo::perception::CameraDevice camera{camera_.toStdString(), camera_.toStdString(), "v4l2", camera_.toStdString()};
  service_ = std::make_unique<elo::perception::VisionService>(camera, detector_, recognizer_);
  connect(service_.get(), &elo::perception::VisionService::statusChanged, this, [this](const QString& text) {
    if (text.startsWith("Apenas uma pessoa")) setAuthorized(false);
    operational_ = text != "Abrindo câmera do totem" && text != "Câmera parada";
    status_ = (text == "Atenção detectada" ? QStringLiteral("Rosto orientado à tela (estimativa)") : text) + " · processamento local"; emit changed();
  });
  connect(service_.get(), &elo::perception::VisionService::failure, this, [this](const QString&) {
    operational_ = false; attention_ = false; setAuthorized(false);
    status_ = "Câmera indisponível · reprodução mantida"; emit changed();
    QTimer::singleShot(5000, this, [this] { service_.reset(); start(); });
  });
  connect(service_.get(), &elo::perception::VisionService::facePresenceChanged, this, [this](bool present) {
    if (!present) setAuthorized(false);
  });
  connect(service_.get(), &elo::perception::VisionService::attentionChanged, this, [this](bool engaged, double) {
    attention_ = engaged; status_ = engaged ? "Rosto orientado à tela · estimativa local" : "Aguardando aproximação"; emit changed();
  });
  connect(service_.get(), &elo::perception::VisionService::faceEmbeddingReady, this, &PerceptionModel::observeEmbedding);
  connect(service_.get(), &elo::perception::VisionService::observationProcessed, this, [this] { ++processed_frames_; });
  service_->start();
}
void PerceptionModel::setAuthorized(bool authorized) {
  authorized_ = authorized && recognitionAvailable();
  query_.fill(0); query_.clear(); identity_.clear(); candidate_.clear(); uncertain_ = false;
  if (service_) service_->setBiometricAuthorized(authorized_);
  status_ = authorized_ ? "Reconhecimento autorizado nesta visita · cadastro só ao escolher Lembrar visita"
                        : "Reconhecimento desligado · presença continua local";
  emit changed();
}
void PerceptionModel::observeEmbedding(const QVector<float>& embedding, double quality) {
  if (!authorized_ || !std::isfinite(quality) || quality < 0.85 || quality > 1 || !valid(embedding)) return;
  query_ = embedding;
  double best = -1, second = -1; QString candidate;
  for (const auto& value : profiles_) {
    const auto profile = value.toObject(); const auto score = similarity(query_, profile["embedding"].toArray());
    if (score > best) { second = best; best = score; candidate = profile["id"].toString(); }
    else second = std::max(second, score);
  }
  uncertain_ = best >= 0.363;
  candidate_ = (best >= 0.50 && best - second >= 0.08) ? candidate : QString{};
  if (!identity_.isEmpty() && identity_ != candidate_) identity_.clear();
  if (!identity_.isEmpty()) candidate_.clear();
  status_ = !candidate_.isEmpty() ? "Visita anterior possível · confirme para retomar"
      : best >= 0.363 ? "Correspondência incerta · nenhuma visita retomada" : "Sem cadastro correspondente · lembrar visita é opcional";
  emit changed();
}
void PerceptionModel::enroll() {
  if (!canEnroll() || profiles_.size() >= 128) return;
  QJsonArray embedding; for (const auto value : query_) embedding.append(value);
  const auto id = QUuid::createUuid().toString(QUuid::WithoutBraces);
  profiles_.append(QJsonObject{{"id", id}, {"embedding", embedding}, {"publication", publication_}, {"page", page_}});
  if (!save()) { profiles_.removeLast(); return; }
  identity_ = id; status_ = "Visita lembrada somente neste totem · pode apagar cadastro"; emit changed();
}
void PerceptionModel::confirmIdentity() {
  if (!authorized_ || candidate_.isEmpty()) return;
  identity_ = candidate_; candidate_.clear(); status_ = "Continuidade confirmada nesta visita"; emit changed();
}
int PerceptionModel::resumePage() const {
  for (const auto& value : profiles_) {
    auto p = value.toObject();
    if (p["id"] == candidate_ && p["publication"] == publication_) return p["page"].toInt();
  }
  return 0;
}
void PerceptionModel::presentation(QString digest, int page) {
  if (publication_ == digest && page_ == page) return;
  publication_ = std::move(digest); page_ = page;
  if (identity_.isEmpty()) return;
  for (int i = 0; i < profiles_.size(); ++i) {
    auto p = profiles_[i].toObject();
    if (p["id"] == identity_) { p["publication"] = publication_; p["page"] = page_; profiles_[i] = p; save(); break; }
  }
}
void PerceptionModel::forget() {
  if (identity_.isEmpty()) return;
  const auto before = profiles_;
  for (int i = 0; i < profiles_.size(); ++i) if (profiles_[i].toObject()["id"] == identity_) { profiles_.removeAt(i); break; }
  if (!save()) { profiles_ = before; return; }
  setAuthorized(false); status_ = "Cadastro apagado deste totem"; emit changed();
}
void PerceptionModel::load() {
  if (gallery_.isEmpty()) return;
  const QFileInfo info(gallery_);
  if (!QDir::isAbsolutePath(gallery_) || info.isSymLink()) { gallery_valid_ = false; return; }
  if (!info.exists()) return;
  QFile file(gallery_);
  if (!file.open(QIODevice::ReadOnly) || (file.permissions() & (QFileDevice::ReadGroup | QFileDevice::WriteGroup | QFileDevice::ReadOther | QFileDevice::WriteOther))) { gallery_valid_ = false; return; }
  const auto bytes = file.read(512 * 1024 + 1);
  const auto obj = QJsonDocument::fromJson(bytes).object();
  if (bytes.size() > 512 * 1024 || obj["schema"].toInt() != 1 || obj["model"] != model_hash_ || !obj["profiles"].isArray() || obj["profiles"].toArray().size() > 128) { gallery_valid_ = false; return; }
  for (const auto& value : obj["profiles"].toArray()) {
    const auto p = value.toObject(); QVector<float> embedding;
    for (const auto& n : p["embedding"].toArray()) { if (!n.isDouble()) { gallery_valid_ = false; return; } embedding.append(float(n.toDouble())); }
    if (p["id"].toString().isEmpty() || !valid(embedding) || p["page"].toInt() < 1 || p["page"].toInt() > 32) { gallery_valid_ = false; return; }
  }
  profiles_ = obj["profiles"].toArray();
}
bool PerceptionModel::save() {
  if (!recognitionAvailable() || QFileInfo(gallery_).isSymLink()) return false;
  QDir parent = QFileInfo(gallery_).dir();
  if (QFileInfo(parent.absolutePath()).isSymLink() || !QDir().mkpath(parent.absolutePath())) return false;
  if (!QFile::setPermissions(parent.absolutePath(), QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner)) return false;
  QSaveFile file(gallery_);
  const auto bytes = QJsonDocument(QJsonObject{{"schema", 1}, {"model", model_hash_}, {"profiles", profiles_}}).toJson(QJsonDocument::Compact);
  if (!file.open(QIODevice::WriteOnly) || !file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner) || file.write(bytes) != bytes.size() || !file.commit()) {
    status_ = "Não foi possível salvar cadastro local"; emit changed(); return false;
  }
  return true;
}
