// SPDX-License-Identifier: GPL-3.0-only
#include "client.hpp"
#include "ports.hpp"
#include <utility>
#include <algorithm>

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
  if (fixture.id.empty() || fixture.name.empty() || (fixture.version != "1" && fixture.version != "2" && fixture.version != "3" && fixture.version != "4" && fixture.version != "5") ||
      fixture.pages.empty() || fixture.pages.size() > 32 || fixture.id.size() > 128 || fixture.name.size() > 256)
    return false;
  if (((fixture.version == "4" || (fixture.version == "5" && fixture.exposure_seconds != 0)) && (fixture.exposure_seconds < 5 || fixture.exposure_seconds > 3600))
      || (fixture.version != "4" && fixture.version != "5" && fixture.exposure_seconds != 0)) return false;
  if (fixture.id.find('\0') != std::string::npos || fixture.name.find('\0') != std::string::npos) return false;
  for (const auto& page : fixture.pages) {
    if (!page.media_source.empty() && (fixture.version != "5" || !page.media_source.starts_with("file:")
        || (page.media_kind != "audio" && page.media_kind != "video") || page.media_hash.size() != 64)) return false;
    if ((page.interaction != "none" && page.interaction != "reveal")
        || (page.interaction == "reveal" && fixture.version != "3" && fixture.version != "4" && fixture.version != "5")) return false;
    if (page.title.empty() || page.title.size() > 256 || page.body.empty() || page.body.size() > 4096)
      return false;
    else if ((!page.image_source.empty() && ((fixture.version != "2" && fixture.version != "3" && fixture.version != "4" && fixture.version != "5") || page.image_source.size() > 2800000
             || (!page.image_source.starts_with("data:image/png;base64,") && !page.image_source.starts_with("data:image/jpeg;base64,"))
             || page.image_alt.empty() || page.image_alt.size() > 512 || page.image_hash.size() != 64))) return false;
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
  revealed_.assign(fixture_.pages.size(), false);
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
bool Client::handle(CheckContent) {
  if (!catalog_ || !usable()) return false;
  const auto previous = content_update_;
  auto result = catalog_->load();
  if (result.status != LoadStatus::loaded || !valid(result.fixture)) {
    pending_.reset();
    content_update_ = ContentUpdate::rejected;
  } else if (result.fixture == fixture_) {
    pending_.reset();
    content_update_ = ContentUpdate::none;
  } else {
    pending_ = std::move(result.fixture);
    content_update_ = ContentUpdate::available;
  }
  return previous != content_update_;
}
bool Client::handle(Reveal) {
  if (!can_reveal()) return false;
  revealed_[index_] = true;
  return true;
}
bool Client::handle(Reset) {
  if (!usable()) return false;
  // Revalidate the current pointer at the session boundary, including revocation
  // or corruption since the last poll. Never apply a stale pending candidate.
  const bool changed = handle(CheckContent{});
  if (pending_) {
    fixture_ = std::move(*pending_);
    revealed_.assign(fixture_.pages.size(), false);
    pending_.reset();
    content_update_ = ContentUpdate::none;
    index_ = 0;
    // Loading new content is not a rendered-frame acknowledgement.
    state_ = State::booting;
    return true;
  }
  const bool interacted = std::any_of(revealed_.begin(), revealed_.end(), [](bool value) { return value; });
  revealed_.assign(fixture_.pages.size(), false);
  if (index_ == 0) return changed || interacted;
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
  if (!loaded_) return {"Iniciando", "Preparando a fixture local de teste."};
  auto page = fixture_.pages[index_];
  if (page.interaction == "reveal" && !fixture_.exposure_seconds && !revealed_[index_]) {
    page.body = "Toque em Revelar para descobrir.";
    page.image_source.clear(); page.image_alt.clear(); page.image_hash.clear();
  }
  return page;
}
}
