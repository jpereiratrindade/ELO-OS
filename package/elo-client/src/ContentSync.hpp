// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "ClientModel.hpp"
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTimer>
#include <QSslConfiguration>
#include <QUrl>
#include <QJsonObject>

class ContentSync final : public QObject {
 public:
  ContentSync(ClientModel& model, QString root, QUrl endpoint, QString token_file,
              QString ca_file, bool allow_loopback_http);
  // Validate configuration before any request. Returns an error without secrets.
  QString configure();
  void start();
 private:
  void fetch();
  void finish();
  void fail();
  void report();
  void scheduleReport();
  ClientModel& model_;
  QString root_;
  QUrl endpoint_;
  QString token_file_;
  QString ca_file_;
  bool insecure_;
  QSslConfiguration tls_;
  QNetworkAccessManager manager_;
  QNetworkReply* reply_ = nullptr;
  QTimer timer_;
  QTimer deadline_;
  QByteArray response_;
  int retry_ms_ = 5000;
  QTimer report_timer_;
  QTimer report_deadline_;
  QNetworkReply* report_reply_ = nullptr;
  QByteArray received_;
  QByteArray presented_;
  QJsonObject display_;
  QString session_;
  quint64 report_sequence_ = 0;
  int report_retry_ms_ = 5000;
  bool report_dirty_ = false;
};
