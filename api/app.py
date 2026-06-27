import json
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network import NetworkOrchestrator

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "universe-config.json")

app = Flask(__name__)
CORS(app)

orchestrator = NetworkOrchestrator(CONFIG_PATH)

with open(CONFIG_PATH) as f:
    _config = json.load(f)
    PLANETS = _config["nodes"]
    METADATA = _config["universe_metadata"]


@app.route("/")
def index():
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ui", "relic-ring-protocol.html"
    )
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/universe", methods=["GET"])
def get_universe():
    topology = orchestrator.router.get_topology()
    void_topo = orchestrator.router.get_void_topology()
    links = []
    for src, neighbors in topology.items():
        for dst, latency in neighbors.items():
            if dst > src:
                links.append({
                    "source": src,
                    "target": dst,
                    "latency_ms": round(latency, 4),
                    "void_latency_ms": round(void_topo.get(src, {}).get(dst, latency), 4)
                })
    return jsonify({
        "metadata": METADATA,
        "planets": PLANETS,
        "links": links,
        "active_planets": list(orchestrator.active_planets),
        "disabled_links": [list(l) for l in orchestrator.disabled_links],
        "blocked_links": orchestrator.router.get_blocked_links()
    })


@app.route("/api/transmit", methods=["POST"])
def transmit():
    data = request.get_json()
    origin = data.get("origin")
    destination = data.get("destination")
    message = data.get("message", "")

    if not origin or not destination or not message:
        return jsonify({"error": "origin, destination and message are required"}), 400

    result = orchestrator.process_transmission_transaction(origin, destination, message)

    if result:
        return jsonify({"success": True, "packet": result.to_dict()})
    else:
        return jsonify({"success": False, "error": "No valid route found. Packet undeliverable."}), 200


@app.route("/api/planet/<planet_id>/kill", methods=["POST"])
def kill_planet(planet_id):
    success = orchestrator.set_planet_operational_status(planet_id, False)
    if not success:
        return jsonify({"error": f"Planet '{planet_id}' not found"}), 404
    return jsonify({"success": True, "message": f"Planet '{planet_id}' is now offline."})


@app.route("/api/planet/<planet_id>/revive", methods=["POST"])
def revive_planet(planet_id):
    success = orchestrator.set_planet_operational_status(planet_id, True)
    if not success:
        return jsonify({"error": f"Planet '{planet_id}' not found"}), 404
    return jsonify({"success": True, "message": f"Planet '{planet_id}' is now online."})


@app.route("/api/link/kill", methods=["POST"])
def kill_link():
    data = request.get_json()
    src = data.get("source")
    dst = data.get("target")
    if not src or not dst:
        return jsonify({"error": "source and target required"}), 400
    orchestrator.set_link_operational_status(src, dst, False)
    return jsonify({"success": True, "message": f"Link {src} <-> {dst} severed."})


@app.route("/api/link/revive", methods=["POST"])
def revive_link():
    data = request.get_json()
    src = data.get("source")
    dst = data.get("target")
    if not src or not dst:
        return jsonify({"error": "source and target required"}), 400
    orchestrator.set_link_operational_status(src, dst, True)
    return jsonify({"success": True, "message": f"Link {src} <-> {dst} restored."})


@app.route("/api/reset", methods=["POST"])
def reset():
    orchestrator.reload_universe_configuration()
    return jsonify({"success": True, "message": "Universe reset. All nodes and links restored."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)