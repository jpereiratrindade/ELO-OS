// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "ports.hpp"
#include <algorithm>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace elo {
// Local test contract. No transport, durable queue or server acknowledgement.
enum class EnqueueResult { inserted, duplicate, conflict, invalid, full };
struct PendingEvent {
  std::string key;
  std::string payload;
  unsigned attempts = 0;
  std::uint64_t due_ms = 0;
  bool acknowledged = false;
  bool exhausted = false;
};
class EventLedger {
 public:
  explicit EventLedger(const Clock& clock) : clock_(clock) {}
  EnqueueResult enqueue(std::string key, std::string payload) {
    if (key.empty() || key.size() > 128 || payload.empty() || payload.size() > 4096)
      return EnqueueResult::invalid;
    const auto it = events_.find(key);
    if (it != events_.end())
      return it->second.payload == payload ? EnqueueResult::duplicate : EnqueueResult::conflict;
    if (events_.size() >= 256) return EnqueueResult::full;
    auto event = PendingEvent{key, std::move(payload), 0, clock_.now_ms()};
    events_.emplace(std::move(key), std::move(event));
    return EnqueueResult::inserted;
  }
  std::vector<PendingEvent> due() const {
    std::vector<PendingEvent> result;
    const auto now = clock_.now_ms();
    for (const auto& [key, event] : events_)
      if (!event.acknowledged && !event.exhausted && event.due_ms <= now) result.push_back(event);
    return result;
  }
  bool attempted(const std::string& key) {
    auto it = events_.find(key);
    if (it == events_.end() || it->second.acknowledged || it->second.exhausted ||
        it->second.due_ms > clock_.now_ms()) return false;
    auto& event = it->second;
    ++event.attempts;
    event.exhausted = event.attempts >= 5;
    event.due_ms = clock_.now_ms() + std::min<std::uint64_t>(1000ULL << (event.attempts - 1), 16000);
    return true;
  }
  bool acknowledge(const std::string& key, const std::string& payload) {
    auto it = events_.find(key);
    if (it == events_.end() || it->second.payload != payload) return false;
    it->second.acknowledged = true;
    return true;
  }
  const PendingEvent* find(const std::string& key) const {
    const auto it = events_.find(key);
    return it == events_.end() ? nullptr : &it->second;
  }
 private:
  const Clock& clock_;
  std::map<std::string, PendingEvent> events_;
};
}
