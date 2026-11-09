// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include "client.hpp"
#include <cstdint>
#include <string>

namespace elo {
// Explicit adapters; constructing the core never starts I/O or background work.
struct StoredContent { LoadStatus status; std::string utf8; };
class LocalStore {
 public:
  virtual ~LocalStore() = default;
  virtual StoredContent read_active() const = 0;
};
class NetworkStatus {
 public:
  virtual ~NetworkStatus() = default;
  virtual bool available() const = 0;  // Local link/address, never authenticated ONLINE.
};
class Clock {
 public:
  virtual ~Clock() = default;
  virtual std::uint64_t now_ms() const = 0;
};
struct PresentedFrame { std::uint64_t sequence = 0; std::uint64_t at_ms = 0; };
class PresentationPort {
 public:
  virtual ~PresentationPort() = default;
  virtual PresentedFrame last_frame() const = 0;
};
class Diagnostics {
 public:
  virtual ~Diagnostics() = default;
  virtual void transition(State from, State to) = 0;
};
}
