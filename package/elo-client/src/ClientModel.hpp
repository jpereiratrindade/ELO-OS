// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "core/client.hpp"
#include <QObject>
#include <QString>

class ClientModel : public QObject {
  Q_OBJECT
  Q_PROPERTY(QString state READ state NOTIFY changed)
  Q_PROPERTY(QString title READ title NOTIFY changed)
  Q_PROPERTY(QString body READ body NOTIFY changed)
  Q_PROPERTY(int pageNumber READ pageNumber NOTIFY changed)
  Q_PROPERTY(int pageCount READ pageCount NOTIFY changed)
  Q_PROPERTY(QString fixtureLabel READ fixtureLabel NOTIFY changed)
  Q_PROPERTY(QString error READ error NOTIFY changed)
  Q_PROPERTY(bool canNext READ canNext NOTIFY changed)
  Q_PROPERTY(bool canPrevious READ canPrevious NOTIFY changed)
 public:
  explicit ClientModel(QObject* parent = nullptr, elo::ContentCatalog* catalog = nullptr)
      : QObject(parent), client_(catalog) {}
  QString state() const;
  QString title() const;
  QString body() const;
  int pageNumber() const { return static_cast<int>(client_.index() + 1); }
  int pageCount() const { return static_cast<int>(client_.page_count()); }
  QString fixtureLabel() const;
  QString error() const;
  bool canNext() const { return client_.can_next(); }
  bool canPrevious() const { return client_.can_previous(); }
  void start();
  void presentationReady();
  Q_INVOKABLE void next();
  Q_INVOKABLE void previous();
  Q_INVOKABLE void reset();
 signals:
  void changed();
 private:
  elo::Client client_;
};
