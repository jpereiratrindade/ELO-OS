// SPDX-License-Identifier: GPL-3.0-only
#include "client.hpp"
#include "ports.hpp"
#include <utility>

namespace elo {
Fixture local_fixture() {
  return {"elo-local-fixture", "Apresentação local de teste", "1", {
    {"Um começo local", "Este espaço está pronto para você. Explore no seu tempo, mesmo sem conexão."},
    {"Observe ao seu redor", "Escolha algo próximo. Que detalhes chamam a sua atenção? Não há uma resposta esperada."},
    {"Você escolhe o próximo passo", "Volte, comece outra vez ou faça uma pausa. Esta apresentação não registra suas respostas."}
  }};
}
namespace {
bool valid(const Fixture& fixture) {
  if (fixture.id.empty() || fixture.name.empty() || fixture.version != "1" ||
      fixture.pages.empty() || fixture.pages.size() > 32 || fixture.id.size() > 128 || fixture.name.size() > 256)
    return false;
  if (fixture.id.find('\0') != std::string::npos || fixture.name.find('\0') != std::string::npos) return false;
  for (const auto& page : fixture.pages) {
    if (page.title.empty() || page.title.size() > 256 || page.body.empty() || page.body.size() > 4096)
      return false;
    else if (page.title.find('\0') != std::string::npos || page.body.find('\0') != std::string::npos) return false;
  }
  return true;
}
}
bool Client::dispatch(const Event& event) {
  const auto before = state_;
  const auto changed = std::visit([this](const auto& value) { return handle(value); }, event);
  if (diagnostics_ && before != state_) diagnostics_->transition(before, state_);
  return changed;
}
bool Client::handle(Start) {
  if (loaded_ || state_ != State::booting) return false;
  auto result = catalog_ ? catalog_->load() : LoadResult{LoadStatus::loaded, local_fixture()};
  if (result.status != LoadStatus::loaded || !valid(result.fixture)) {
    state_ = result.status == LoadStatus::fatal ? State::error_fatal : State::error_recoverable;
    switch (result.status) {
      case LoadStatus::missing: error_ = "Fixture local ausente."; break;
      case LoadStatus::timeout: error_ = "Tempo de carga da fixture excedido."; break;
      case LoadStatus::fatal: error_ = "Falha fatal no catálogo local."; break;
      default: error_ = "Fixture local inválida ou incompatível."; break;
    }
    return true;
  }
  fixture_ = std::move(result.fixture);
  loaded_ = true;
  // Remain BOOTING until the presentation adapter acknowledges a rendered frame.
  return true;
}
bool Client::handle(PresentationReady event) {
  if (!loaded_ || state_ != State::booting) return false;
  if (!event.success) {
    state_ = State::error_recoverable;
    error_ = "Não foi possível apresentar a fixture local.";
  } else {
    state_ = State::ready_local;
  }
  return true;
}
bool Client::handle(Next) {
  if (!can_next()) return false;
  ++index_;
  return true;
}
bool Client::handle(Previous) {
  if (!can_previous()) return false;
  --index_;
  return true;
}
bool Client::handle(Reset) {
  if (!usable() || index_ == 0) return false;
  index_ = 0;
  return true;
}
bool Client::handle(NetworkChanged event) {
  if (network_available_ == event.available) return false;
  network_available_ = event.available;
  if (usable()) state_ = event.available ? State::ready_local : State::degraded_offline;
  return true;
}
bool Client::handle(Retry) {
  if (state_ != State::error_recoverable) return false;
  fixture_ = {};
  loaded_ = false;
  index_ = 0;
  error_.clear();
  state_ = State::booting;
  return handle(Start{});
}
std::string_view Client::state_name() const {
  return elo::state_name(state_);
}
std::string_view state_name(State state) {
  switch (state) {
    case State::booting: return "BOOTING";
    case State::ready_local: return "READY_LOCAL";
    case State::connecting: return "CONNECTING";
    case State::online: return "ONLINE";
    case State::degraded_offline: return "DEGRADED_OFFLINE";
    case State::update_staged: return "UPDATE_STAGED";
    case State::validating: return "VALIDATING";
    case State::error_recoverable: return "ERROR_RECOVERABLE";
    case State::restarting: return "RESTARTING";
    case State::error_fatal: return "ERROR_FATAL";
  }
  return "ERROR_FATAL";
}
Page Client::page() const {
  if (!error_.empty()) return {"Apresentação indisponível", error_};
  return loaded_ ? fixture_.pages[index_] : Page{"Iniciando", "Preparando a fixture local de teste."};
}
}
