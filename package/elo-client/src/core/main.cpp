// SPDX-License-Identifier: GPL-3.0-only
#include "client.hpp"
#include <iostream>

int main() {
  elo::Client client;
  std::cout << "state=" << client.state_name() << '\n';
  client.start();
  const auto first = client.page();
  std::cout << "fixture=" << client.fixture().id << " version=" << client.fixture().version << '\n'
            << first.title << '\n' << first.body << std::endl;
  if (!std::cout.good()) return 1;
  client.dispatch(elo::PresentationReady{true});
  if (!client.usable()) return 1;
  std::cout << "state=" << client.state_name() << '\n';
  do {
    const auto page = client.page();
    std::cout << "page=" << client.index() + 1 << '/' << client.page_count() << '\n'
              << page.title << '\n' << page.body << '\n';
  } while (client.next());
  return std::cout.good() ? 0 : 1;
}
