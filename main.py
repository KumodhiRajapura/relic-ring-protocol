import sys
import json
import os

from core.network import NetworkOrchestrator
from ui.visualizer import (
    print_header, print_universe_info, print_topology_table,
    visualize_universe, print_packet_result, print_encoding_trace,
    print_chaos_event, bold, cyan, yellow, green, red, dim,
    bright_cyan, bright_yellow, bright_green, magenta
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "universe-config.json")


def get_planet_list(orchestrator: NetworkOrchestrator) -> list:
    import json
    with open(orchestrator.config_filepath) as f:
        return json.load(f)["nodes"]


def print_menu(dead_planets: set, dead_links: set):
    print(bold(cyan("\n┌─── MISSION CONTROL ─────────────────────────────────────────────┐")))
    print(f"  {bold('1')}  Send a message between planets")
    print(f"  {bold('2')}  View star-map (universe topology)")
    print(f"  {bold('3')}  Kill a planet  (chaos test)")
    print(f"  {bold('4')}  Revive a planet")
    print(f"  {bold('5')}  Kill a link    (chaos test)")
    print(f"  {bold('6')}  Revive a link")
    print(f"  {bold('7')}  Show planet & network info")
    print(f"  {bold('8')}  Run demo transmission (Hello world: Aegis → Caelum)")
    print(f"  {bold('9')}  Reset universe (restore all)")
    print(f"  {bold('0')}  Exit")
    if dead_planets:
        print(f"  {red('☠ Dead planets: ' + ', '.join(sorted(dead_planets)))}")
    if dead_links:
        dead_links_str = ', '.join(f"{a}-{b}" for a, b in sorted(dead_links))
        print(f"  {red('✗ Dead links: ' + dead_links_str)}")
    print(bold(cyan("└─────────────────────────────────────────────────────────────────┘")))
    print()


def prompt_planet(planets: list, prompt: str, exclude: str = None) -> str:
    ids = [p["id"] for p in planets]
    while True:
        print(f"  Planets: {', '.join(bright_cyan(p) for p in ids)}")
        val = input(f"  {prompt}: ").strip()
        if val in ids and val != exclude:
            return val
        print(red(f"  Invalid planet. Choose from: {', '.join(ids)}"))


def send_transmission(orchestrator: NetworkOrchestrator, planets: list,
                      dead_planets: set, dead_links: set):
    print(bold(cyan("\n  ─── Send Transmission ──────────────────────────────────────────")))
    origin = prompt_planet(planets, "Origin planet")
    destination = prompt_planet(planets, "Destination planet", exclude=origin)
    message = input(f"  Message to send: ").strip()
    if not message:
        print(red("  No message entered."))
        return

    print(f"\n  Routing {bright_cyan(origin)} → {bright_cyan(destination)} …")

    result = orchestrator.process_transmission_transaction(origin, destination, message)
    print_packet_result(result, message)

    if result:
        route = result.route_taken
        print_encoding_trace(message, route, planets)
        visualize_universe(planets, orchestrator.router.get_topology(),
                           dead_planets=dead_planets, dead_links=dead_links,
                           active_route=route)


def chaos_kill_planet(orchestrator: NetworkOrchestrator, planets: list,
                      dead_planets: set):
    print(bold(red("\n  ─── Kill Planet (Chaos Test) ───────────────────────────────────")))
    alive = [p for p in planets if p["id"] not in dead_planets]
    if not alive:
        print(red("  All planets already dead!"))
        return
    planet_id = prompt_planet(alive, "Planet to kill")
    orchestrator.set_planet_operational_status(planet_id, False)
    dead_planets.add(planet_id)
    print_chaos_event(f"Planet '{planet_id}' OFFLINE", "Node removed from routing topology.", is_kill=True)


def chaos_revive_planet(orchestrator: NetworkOrchestrator, planets: list,
                        dead_planets: set):
    print(bold(green("\n  ─── Revive Planet ──────────────────────────────────────────────")))
    dead = [p for p in planets if p["id"] in dead_planets]
    if not dead:
        print(green("  No dead planets to revive."))
        return
    planet_id = prompt_planet(dead, "Planet to revive")
    orchestrator.set_planet_operational_status(planet_id, True)
    dead_planets.discard(planet_id)
    print_chaos_event(f"Planet '{planet_id}' ONLINE", "Node restored to routing topology.", is_kill=False)


def chaos_kill_link(orchestrator: NetworkOrchestrator, planets: list,
                    dead_planets: set, dead_links: set):
    print(bold(red("\n  ─── Kill Link (Chaos Test) ─────────────────────────────────────")))
    topology = orchestrator.router.get_topology()
    available = []
    for src in topology:
        for dst in topology[src]:
            link = tuple(sorted((src, dst)))
            if link not in dead_links and link not in [(tuple(sorted((a, b)))) for a, b in dead_links]:
                if link not in available:
                    available.append(link)

    if not available:
        print(red("  No active links to kill."))
        return

    print("  Active links:")
    for i, (a, b) in enumerate(available):
        print(f"    {i+1}. {bright_cyan(a)} ──── {bright_cyan(b)}")
    try:
        choice = int(input("  Choose link number: ").strip()) - 1
        if 0 <= choice < len(available):
            link = available[choice]
            orchestrator.set_link_operational_status(link[0], link[1], False)
            dead_links.add(link)
            print_chaos_event(f"Link {link[0]}↔{link[1]} SEVERED",
                              "Direct path removed from routing topology.", is_kill=True)
        else:
            print(red("  Invalid choice."))
    except ValueError:
        print(red("  Invalid input."))


def chaos_revive_link(orchestrator: NetworkOrchestrator, dead_links: set):
    print(bold(green("\n  ─── Revive Link ────────────────────────────────────────────────")))
    if not dead_links:
        print(green("  No dead links to revive."))
        return
    dead = list(dead_links)
    for i, (a, b) in enumerate(dead):
        print(f"    {i+1}. {bright_cyan(a)} ──── {bright_cyan(b)}")
    try:
        choice = int(input("  Choose link number: ").strip()) - 1
        if 0 <= choice < len(dead):
            link = dead[choice]
            orchestrator.set_link_operational_status(link[0], link[1], True)
            dead_links.discard(link)
            print_chaos_event(f"Link {link[0]}↔{link[1]} RESTORED",
                              "Direct path re-added to routing topology.", is_kill=False)
        else:
            print(red("  Invalid choice."))
    except ValueError:
        print(red("  Invalid input."))


def run_demo(orchestrator: NetworkOrchestrator, planets: list,
             dead_planets: set, dead_links: set):
    """Demo: Hello world from Aegis (B8) → Boreas (B5) → Caelum (B14)"""
    print(bold(magenta("\n  ═══ DEMO TRANSMISSION: Hello world — Aegis → Caelum ═══")))
    origin, destination, message = "Aegis", "Caelum", "Hello world"
    print(f"  Sending {bright_yellow(repr(message))} from "
          f"{bright_cyan(origin)} to {bright_cyan(destination)} …\n")

    result = orchestrator.process_transmission_transaction(origin, destination, message)
    print_packet_result(result, message)

    if result:
        route = result.route_taken
        print_encoding_trace(message, route, planets)
        visualize_universe(planets, orchestrator.router.get_topology(),
                           dead_planets=dead_planets, dead_links=dead_links,
                           active_route=route)


def main():
    print_header()
    print(f"  Loading universe from: {dim(CONFIG_PATH)}")

    try:
        orchestrator = NetworkOrchestrator(CONFIG_PATH)
    except Exception as e:
        print(red(f"  ✗ Failed to load universe: {e}"))
        sys.exit(1)

    planets = get_planet_list(orchestrator)

    with open(CONFIG_PATH) as f:
        metadata = json.load(f)["universe_metadata"]

    dead_planets: set = set()
    dead_links: set = set()

    print_universe_info(planets, metadata)
    print("  Universe initialized successfully. Welcome to Zeta-26.\n")

    while True:
        print_menu(dead_planets, dead_links)
        choice = input(bold("  COMMAND > ")).strip()

        if choice == "1":
            send_transmission(orchestrator, planets, dead_planets, dead_links)

        elif choice == "2":
            visualize_universe(planets, orchestrator.router.get_topology(),
                               dead_planets=dead_planets, dead_links=dead_links)
            print_topology_table(planets, orchestrator.router.get_topology())

        elif choice == "3":
            chaos_kill_planet(orchestrator, planets, dead_planets)

        elif choice == "4":
            chaos_revive_planet(orchestrator, planets, dead_planets)

        elif choice == "5":
            chaos_kill_link(orchestrator, planets, dead_planets, dead_links)

        elif choice == "6":
            chaos_revive_link(orchestrator, dead_links)

        elif choice == "7":
            print_universe_info(planets, metadata)
            print_topology_table(planets, orchestrator.router.get_topology())

        elif choice == "8":
            run_demo(orchestrator, planets, dead_planets, dead_links)

        elif choice == "9":
            orchestrator.reload_universe_configuration()
            dead_planets.clear()
            dead_links.clear()
            print(bright_green("\n  ✦ Universe reset — all nodes and links restored.\n"))

        elif choice == "0":
            print(bright_cyan("\n  Shutting down Relic Ring Protocol. Aether-Net memorial: never forget.\n"))
            break

        else:
            print(red("  Unknown command. Please choose 0-9."))


if __name__ == "__main__":
    main()