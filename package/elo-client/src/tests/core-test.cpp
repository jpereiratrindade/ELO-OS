// SPDX-License-Identifier: GPL-3.0-only
#include "core/client.hpp"
#include "core/events.hpp"
#include <cstdlib>
#include <iostream>

void check(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
  }
}
struct Catalog : elo::ContentCatalog {
  elo::LoadResult result{elo::LoadStatus::loaded, elo::local_fixture()};
  elo::LoadResult load() override { return result; }
};
int main() {
  elo::Client client;
  check(client.state_name() == "BOOTING", "initial state");
  check(!client.next() && !client.previous() && !client.reset(), "no navigation before readiness");
  check(!client.dispatch(elo::PresentationReady{true}), "no readiness without fixture");
  check(client.start() && client.state_name() == "BOOTING", "load is not presentation health");
  check(!client.next(), "no navigation before presentation acknowledgement");
  check(client.dispatch(elo::PresentationReady{true}) && client.state_name() == "READY_LOCAL", "local readiness");
  check(!client.start() && !client.previous(), "idempotent startup and first-page boundary");
  const auto first = client.page().title;
  for (std::size_t i = 0; i < client.page_count(); ++i) {
    check(client.index() == i && !client.page().title.empty() && !client.page().body.empty(), "local content");
    if (i + 1 < client.page_count()) check(client.next(), "next page");
  }
  check(!client.next() && client.page().title != first, "last-page boundary");
  check(!client.start() && client.index() == client.page_count() - 1, "start preserves current page");
  check(client.previous() && client.index() == client.page_count() - 2, "previous page");
  check(client.reset() && client.page().title == first && !client.reset(), "reset");
  check(!client.dispatch(elo::NetworkChanged{false}) && client.usable(), "offline before boot is usable");
  check(client.dispatch(elo::NetworkChanged{true}) && client.state() != elo::State::online, "link is not authenticated ONLINE");
  client.next();
  const auto page = client.page().title;
  check(client.dispatch(elo::NetworkChanged{false}) && client.state_name() == "DEGRADED_OFFLINE", "network loss");
  check(client.page().title == page && client.usable(), "network loss preserves presentation");
  check(!client.dispatch(elo::NetworkChanged{false}), "duplicate network event");
  check(client.dispatch(elo::NetworkChanged{true}) && client.page().title == page, "reconnection preserves presentation");
  elo::Client independent;
  independent.start();
  independent.dispatch(elo::PresentationReady{true});
  check(independent.index() == 0, "independent sessions");
  for (auto status : {elo::LoadStatus::missing, elo::LoadStatus::invalid, elo::LoadStatus::timeout, elo::LoadStatus::fatal}) {
    Catalog catalog;
    catalog.result.status = status;
    elo::Client failed(&catalog);
    failed.start();
    check(!failed.usable() && !failed.error().empty() && !failed.dispatch(elo::PresentationReady{true}), "failed load never READY");
    if (status != elo::LoadStatus::fatal) {
      catalog.result = {elo::LoadStatus::loaded, elo::local_fixture()};
      check(failed.dispatch(elo::Retry{}), "explicit retry");
      check(failed.dispatch(elo::PresentationReady{true}) && failed.usable(), "recover from load failure");
    } else check(!failed.dispatch(elo::Retry{}), "fatal failure is not silently retried");
  }
  for (int corruption = 0; corruption < 5; ++corruption) {
    Catalog catalog;
    switch (corruption) {
      case 0: catalog.result.fixture.version = "unsupported"; break;
      case 1: catalog.result.fixture.pages.clear(); break;
      case 2: catalog.result.fixture.pages[0].body.clear(); break;
      case 3: catalog.result.fixture.pages[0].body.resize(4097, 'x'); break;
      case 4: catalog.result.fixture.id = std::string("hidden\0identity", 15); break;
    }
    elo::Client failed(&catalog);
    failed.start();
    check(!failed.usable() && failed.state_name() == "ERROR_RECOVERABLE", "invalid fixture rejected");
  }
  elo::Client failed_presentation;
  failed_presentation.start();
  check(failed_presentation.dispatch(elo::PresentationReady{false}) && !failed_presentation.usable(), "render failure never READY");
  check(!failed_presentation.dispatch(elo::PresentationReady{true}), "late frame cannot hide failure");
  struct FakeClock : elo::Clock {
    std::uint64_t tick = 0;
    std::uint64_t now_ms() const override { return tick; }
  } clock;
  elo::EventLedger ledger(clock);
  check(ledger.enqueue("test-1", "fixture-event") == elo::EnqueueResult::inserted, "event inserted");
  check(ledger.enqueue("test-1", "fixture-event") == elo::EnqueueResult::duplicate, "same key and bytes are idempotent");
  check(ledger.enqueue("test-1", "different") == elo::EnqueueResult::conflict, "conflicting payload rejected");
  check(ledger.due().size() == 1 && ledger.attempted("test-1"), "first local send attempt");
  check(ledger.due().empty() && !ledger.attempted("test-1"), "no resend before deadline");
  clock.tick = 1000;
  check(ledger.due().size() == 1 && ledger.attempted("test-1"), "retry after injected clock advances");
  check(!ledger.acknowledge("test-1", "wrong"), "ack payload must match");
  check(ledger.acknowledge("test-1", "fixture-event") && ledger.acknowledge("test-1", "fixture-event"), "local ack is idempotent");
  check(ledger.enqueue("test-1", "fixture-event") == elo::EnqueueResult::duplicate && ledger.due().empty(), "acknowledged key is retained");
  check(ledger.enqueue("test-2", "bounded-retries") == elo::EnqueueResult::inserted, "second event");
  for (unsigned attempt = 0; attempt < 5; ++attempt) {
    clock.tick = ledger.find("test-2")->due_ms;
    check(ledger.attempted("test-2"), "bounded attempt");
  }
  check(ledger.find("test-2")->exhausted && !ledger.attempted("test-2") && ledger.due().empty(), "exhausted event retained without infinite retry");
  struct RecordingDiagnostics : elo::Diagnostics {
    unsigned transitions = 0;
    void transition(elo::State, elo::State) override { ++transitions; }
  } diagnostics;
  elo::Client observed(nullptr, &diagnostics);
  observed.start();
  observed.dispatch(elo::PresentationReady{true});
  observed.dispatch(elo::PresentationReady{true});
  check(diagnostics.transitions == 1, "explicit diagnostics record real transitions only");
  std::cout << "PASS elo-core: fixture, presentation, offline, retry and local idempotent events\n";
}
