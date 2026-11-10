// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace elo {
class Diagnostics;
enum class State { booting, ready_local, connecting, online, degraded_offline,
                   update_staged, validating, error_recoverable, restarting, error_fatal };
std::string_view state_name(State state);
struct Page {
  std::string title;
  std::string body;
  std::string image_source;
  std::string image_alt;
  std::string image_hash;
  bool operator==(const Page&) const = default;
};
struct Fixture {
  std::string id;
  std::string name;
  std::string version;
  std::vector<Page> pages;
  std::string content_hash;  // Exact validated local payload bytes; empty for built-in content.
  bool operator==(const Fixture&) const = default;
};
enum class LoadStatus { loaded, missing, invalid, timeout, fatal };
struct LoadResult { LoadStatus status; Fixture fixture; };
class ContentCatalog {
 public:
  virtual ~ContentCatalog() = default;
  virtual LoadResult load() = 0;
};
struct Start {};
struct Next {};
struct Previous {};
struct Reset {};
struct CheckContent {};
enum class ContentUpdate { none, available, rejected };
struct PresentationReady { bool success; };
struct NetworkChanged { bool available; };
struct Retry {};
using Event = std::variant<Start, Next, Previous, Reset, PresentationReady, NetworkChanged, Retry, CheckContent>;
// The core performs no I/O. A loaded fixture and an actual presentation acknowledgement
// are both required for READY_LOCAL. Link availability never establishes ONLINE.
class Client {
 public:
  explicit Client(ContentCatalog* catalog = nullptr, Diagnostics* diagnostics = nullptr)
      : catalog_(catalog), diagnostics_(diagnostics) {}
  bool dispatch(const Event& event);
  bool start() { return dispatch(Start{}); }
  bool next() { return dispatch(Next{}); }
  bool previous() { return dispatch(Previous{}); }
  bool reset() { return dispatch(Reset{}); }
  State state() const { return state_; }
  std::string_view state_name() const;
  std::string_view error() const { return error_; }
  Page page() const;
  const Fixture& fixture() const { return fixture_; }
  ContentUpdate content_update() const { return content_update_; }
  std::size_t index() const { return index_; }
  std::size_t page_count() const { return fixture_.pages.size(); }
  bool usable() const { return state_ == State::ready_local || state_ == State::degraded_offline; }
  bool can_next() const { return usable() && index_ + 1 < page_count(); }
  bool can_previous() const { return usable() && index_ > 0; }
 private:
  bool handle(Start);
  bool handle(Next);
  bool handle(Previous);
  bool handle(Reset);
  bool handle(CheckContent);
  bool handle(PresentationReady event);
  bool handle(NetworkChanged event);
  bool handle(Retry);
  ContentCatalog* catalog_;
  Diagnostics* diagnostics_;
  State state_ = State::booting;
  Fixture fixture_;
  std::string error_;
  std::size_t index_ = 0;
  std::optional<Fixture> pending_;
  ContentUpdate content_update_ = ContentUpdate::none;
  bool loaded_ = false;
  bool network_available_ = false;
};
Fixture local_fixture();
}
