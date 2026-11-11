// SPDX-License-Identifier: GPL-3.0-only
// Adapted from ELO src/perception; transient local preview, no frame persistence.
#include "VisionService.hpp"

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/objdetect/face.hpp>
#include <opencv2/videoio.hpp>

#include <atomic>
#include <chrono>
#include <cmath>
#include <string>
#include <thread>
#include <utility>

namespace elo::perception {
namespace {

constexpr int capture_width = 640;
constexpr int capture_height = 480;
constexpr int capture_fps = 15;
constexpr int frames_required_for_presence = 3;
constexpr int frames_required_for_absence = 10;
constexpr int frames_required_for_attention = 8;
constexpr int frames_required_to_drop_attention = 12;
constexpr auto embedding_interval = std::chrono::milliseconds(400);

bool open_camera(const CameraDevice& camera, cv::VideoCapture& capture) {
    if (camera.backend == "libcamera") {
        std::string camera_id;
        camera_id.reserve(camera.id.size());
        for (const char character : camera.id) {
            if (character == '\\' || character == '"') {
                camera_id.push_back('\\');
            }
            camera_id.push_back(character);
        }
        const std::string pipeline =
            "libcamerasrc camera-name=\"" + camera_id +
            "\" ! video/x-raw,width=640,height=480,framerate=15/1 "
            "! videoconvert ! video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false";
        return capture.open(pipeline, cv::CAP_GSTREAMER);
    }

    if (!capture.open(camera.device_path, cv::CAP_V4L2)) {
        return false;
    }
    capture.set(cv::CAP_PROP_FRAME_WIDTH, capture_width);
    capture.set(cv::CAP_PROP_FRAME_HEIGHT, capture_height);
    capture.set(cv::CAP_PROP_FPS, capture_fps);
    capture.set(cv::CAP_PROP_BUFFERSIZE, 1);
    return true;
}

cv::Mat best_face(const cv::Mat& faces) {
    if (faces.empty()) {
        return {};
    }

    int best_index = -1;
    float best_score = 0.65F;
    for (int row = 0; row < faces.rows; ++row) {
        const float score = faces.at<float>(row, 14);
        const float width = faces.at<float>(row, 2);
        const float height = faces.at<float>(row, 3);
        // Filtra ruído e falsos positivos em fundos estáticos
        if (score >= best_score && width >= 45.0F && height >= 45.0F) {
            best_score = score;
            best_index = row;
        }
    }
    if (best_index < 0) {
        return {};
    }
    return faces.row(best_index);
}

bool evaluate_face_attention(const cv::Mat& face) {
    if (face.empty() || face.cols < 15) {
        return false;
    }

    const float box_w = face.at<float>(0, 2);
    const float box_h = face.at<float>(0, 3);
    // Minimum face size in pixels; no physical distance or cognitive inference.
    if (box_w < 70.0F || box_h < 70.0F) {
        return false;
    }

    const float eye1_x = face.at<float>(0, 4);
    const float eye1_y = face.at<float>(0, 5);
    const float eye2_x = face.at<float>(0, 6);
    const float eye2_y = face.at<float>(0, 7);
    const float nose_x = face.at<float>(0, 8);
    const float nose_y = face.at<float>(0, 9);
    const float mouth1_y = face.at<float>(0, 11);
    const float mouth2_y = face.at<float>(0, 13);

    // 1. Orientação horizontal (Yaw): nariz simétrico entre os dois olhos
    const float min_eye_x = std::min(eye1_x, eye2_x);
    const float max_eye_x = std::max(eye1_x, eye2_x);
    const float eye_span_x = max_eye_x - min_eye_x;
    if (eye_span_x < 12.0F) {
        return false;
    }
    const float yaw_ratio = (nose_x - min_eye_x) / eye_span_x;
    if (yaw_ratio < 0.32F || yaw_ratio > 0.68F) {
        return false;
    }

    // 2. Orientação vertical (Pitch): nariz proporcional entre olhos e boca
    const float eye_mid_y = (eye1_y + eye2_y) * 0.5F;
    const float mouth_mid_y = (mouth1_y + mouth2_y) * 0.5F;
    const float face_v_span = mouth_mid_y - eye_mid_y;
    if (face_v_span < 12.0F) {
        return false;
    }
    const float pitch_ratio = (nose_y - eye_mid_y) / face_v_span;
    if (pitch_ratio < 0.25F || pitch_ratio > 0.75F) {
        return false;
    }

    return true;
}

QImage preview_image(
    const cv::Mat& bgr_frame,
    const cv::Mat& face,
    bool authorized,
    bool recognition_confirmed,
    bool attention_active) {
    cv::Mat annotated = bgr_frame.clone();
    if (!face.empty()) {
        const cv::Rect bounds{
            static_cast<int>(std::lround(face.at<float>(0, 0))),
            static_cast<int>(std::lround(face.at<float>(0, 1))),
            static_cast<int>(std::lround(face.at<float>(0, 2))),
            static_cast<int>(std::lround(face.at<float>(0, 3)))
        };
        const auto color = (authorized || recognition_confirmed)
            ? cv::Scalar(52, 211, 153)
            : (attention_active ? cv::Scalar(245, 159, 8) : cv::Scalar(8, 159, 245));
        cv::rectangle(annotated, bounds, color, 2);
        const auto* label = recognition_confirmed
            ? "visita confirmada"
            : (authorized ? "reconhecendo..."
                          : (attention_active ? "rosto orientado" : "presenca detectada"));
        cv::putText(
            annotated,
            label,
            cv::Point(std::max(0, bounds.x), std::max(24, bounds.y - 8)),
            cv::FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv::LINE_AA);
    }

    cv::Mat rgb;
    cv::cvtColor(annotated, rgb, cv::COLOR_BGR2RGB);
    QImage image(rgb.data, rgb.cols, rgb.rows, static_cast<qsizetype>(rgb.step), QImage::Format_RGB888);
    auto copy = image.copy();
    annotated.setTo(0);
    rgb.setTo(0);
    return copy;
}

QVector<float> extract_embedding(
    const cv::Mat& frame,
    const cv::Mat& face,
    const cv::Ptr<cv::FaceRecognizerSF>& recognizer) {
    cv::Mat aligned;
    cv::Mat feature;
    recognizer->alignCrop(frame, face, aligned);
    recognizer->feature(aligned, feature);

    cv::Mat flat = feature.reshape(1, 1);
    QVector<float> embedding;
    embedding.reserve(flat.cols);
    for (int column = 0; column < flat.cols; ++column) {
        embedding.push_back(flat.at<float>(0, column));
    }

    aligned.setTo(0);
    feature.setTo(0);
    return embedding;
}

} // namespace

struct VisionService::Impl {
    CameraDevice camera;
    QString detector_model_path;
    QString recognizer_model_path;
    VisionService* owner;
    std::jthread worker;
    std::atomic_bool biometric_authorized{false};
    std::atomic_bool recognition_confirmed{false};
    std::atomic_bool running{false};

    Impl(CameraDevice selected_camera, QString detector_path, QString recognizer_path,
         VisionService* service_owner)
        : camera{std::move(selected_camera)},
          detector_model_path{std::move(detector_path)},
          recognizer_model_path{std::move(recognizer_path)},
          owner{service_owner} {}

    void run(std::stop_token stop_token) {
        try {
            emit owner->statusChanged(QStringLiteral("Abrindo câmera do totem"));

            cv::VideoCapture capture;
            if (!open_camera(camera, capture)) {
                emit owner->failure(QStringLiteral("Não foi possível abrir a câmera configurada"));
                return;
            }

            auto detector = cv::FaceDetectorYN::create(
                detector_model_path.toStdString(), "", cv::Size(320, 320), 0.85F, 0.3F, 5000);
            cv::Ptr<cv::FaceRecognizerSF> recognizer;
            if (!recognizer_model_path.isEmpty()) recognizer = cv::FaceRecognizerSF::create(recognizer_model_path.toStdString(), "");
            emit owner->statusChanged(QStringLiteral("Aguardando rosto"));

            bool presence_reported = false;
            int present_frames = 0;
            int absent_frames = 0;
            bool attention_reported = false;
            int focused_frames = 0;
            int unfocused_frames = 0;
            auto attention_start_time = std::chrono::steady_clock::now();
            auto last_dwell_update = std::chrono::steady_clock::now();
            auto last_embedding = std::chrono::steady_clock::now() - embedding_interval;

            bool multiple_faces_reported = false;

            while (!stop_token.stop_requested()) {
                cv::Mat frame;
                if (!capture.read(frame) || frame.empty()) {
                    emit owner->failure(QStringLiteral("A câmera deixou de fornecer frames"));
                    break;
                }

                detector->setInputSize(frame.size());
                cv::Mat faces;
                detector->detect(frame, faces);
                emit owner->observationProcessed();
                auto face = best_face(faces);
                const bool face_present = !face.empty();
                const bool single_face = faces.rows == 1;

                if (face_present) {
                    ++present_frames;
                    absent_frames = 0;

                    const bool instant_focused = evaluate_face_attention(face);
                    if (instant_focused) {
                        ++focused_frames;
                        unfocused_frames = 0;
                    } else {
                        focused_frames = 0;
                        ++unfocused_frames;
                    }
                } else {
                    present_frames = 0;
                    ++absent_frames;
                    focused_frames = 0;
                    ++unfocused_frames;
                }

                if (!presence_reported && present_frames >= frames_required_for_presence) {
                    presence_reported = true;
                    emit owner->facePresenceChanged(true);
                    emit owner->statusChanged(QStringLiteral("Rosto detectado"));
                } else if (presence_reported && absent_frames >= frames_required_for_absence) {
                    presence_reported = false;
                    if (attention_reported) {
                        attention_reported = false;
                        emit owner->attentionChanged(false, 0.0);
                    }
                    emit owner->facePresenceChanged(false);
                    emit owner->statusChanged(QStringLiteral("Aguardando rosto"));
                }

                // Avaliação de Atenção (permanência e orientação com presença confirmada)
                const auto now = std::chrono::steady_clock::now();
                if (presence_reported) {
                    if (!attention_reported && focused_frames >= frames_required_for_attention) {
                        attention_reported = true;
                        attention_start_time = now;
                        last_dwell_update = now;
                        emit owner->attentionChanged(true, 0.5);
                        emit owner->statusChanged(QStringLiteral("Atenção detectada"));
                    } else if (attention_reported) {
                        if (unfocused_frames >= frames_required_to_drop_attention) {
                            attention_reported = false;
                            emit owner->attentionChanged(false, 0.0);
                            emit owner->statusChanged(QStringLiteral("Rosto detectado"));
                        } else if (now - last_dwell_update >= std::chrono::milliseconds(500)) {
                            last_dwell_update = now;
                            const double dwell = std::chrono::duration<double>(
                                now - attention_start_time).count();
                            emit owner->attentionChanged(true, dwell);
                        }
                    }
                } else if (attention_reported) {
                    attention_reported = false;
                    emit owner->attentionChanged(false, 0.0);
                }

                const bool authorized = biometric_authorized.load(std::memory_order_relaxed);
                const bool confirmed = recognition_confirmed.load(std::memory_order_relaxed);
                if (authorized && faces.rows > 1 && !multiple_faces_reported) {
                    multiple_faces_reported = true;
                    emit owner->statusChanged(
                        QStringLiteral("Apenas uma pessoa deve permanecer diante do totem"));
                } else if (faces.rows <= 1 && multiple_faces_reported) {
                    multiple_faces_reported = false;
                    emit owner->statusChanged(
                        face_present ? QStringLiteral("Rosto detectado")
                                     : QStringLiteral("Aguardando rosto"));
                }

                if (presence_reported && single_face && authorized && !recognizer.empty() &&
                    now - last_embedding >= embedding_interval) {
                    auto embedding = extract_embedding(frame, face, recognizer);
                    if (!embedding.empty()) {
                        emit owner->faceEmbeddingReady(embedding, face.at<float>(0, 14));
                        last_embedding = now;
                    }
                }

                emit owner->frameReady(preview_image(frame, face, authorized, confirmed, attention_reported));
                frame.setTo(0);
                faces.setTo(0);
            }

            capture.release();
            emit owner->statusChanged(QStringLiteral("Câmera parada"));
        } catch (const cv::Exception& error) {
            emit owner->failure(QString::fromUtf8(error.what()));
        } catch (const std::exception& error) {
            emit owner->failure(QString::fromUtf8(error.what()));
        }
        running.store(false, std::memory_order_relaxed);
    }
};

VisionService::VisionService(
    CameraDevice camera,
    QString detector_model_path,
    QString recognizer_model_path,
    QObject* parent)
    : QObject(parent),
      impl_{std::make_unique<Impl>(
          std::move(camera),
          std::move(detector_model_path),
          std::move(recognizer_model_path),
          this)} {}

VisionService::~VisionService() {
    stop();
}

void VisionService::start() {
    if (impl_->running.exchange(true, std::memory_order_relaxed)) {
        return;
    }
    impl_->worker = std::jthread([this](std::stop_token token) { impl_->run(token); });
}

void VisionService::stop() {
    if (impl_->worker.joinable()) {
        impl_->worker.request_stop();
        impl_->worker.join();
    }
    impl_->running.store(false, std::memory_order_relaxed);
}

void VisionService::setBiometricAuthorized(bool authorized) {
    impl_->biometric_authorized.store(authorized, std::memory_order_relaxed);
}

void VisionService::setRecognitionConfirmed(bool confirmed) {
    impl_->recognition_confirmed.store(confirmed, std::memory_order_relaxed);
}

} // namespace elo::perception
