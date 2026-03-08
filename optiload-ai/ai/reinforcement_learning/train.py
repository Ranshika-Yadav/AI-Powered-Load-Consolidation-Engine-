"""
RL Training Script — OptiLoad AI
Trains DQN agent on synthetic or real logistics data.
Run: python train.py
"""
import logging
import json
from dqn_agent import DQNAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Synthetic data for standalone training
DEMO_SHIPMENTS = [
    {"shipment_id": f"ship-{i:03d}", "weight": 500 + i * 50, "volume": 2 + i * 0.5,
     "origin_lat": 19.0 + i * 0.05, "origin_lng": 72.8 + i * 0.03,
     "destination_lat": 12.9 + i * 0.04, "destination_lng": 77.6 + i * 0.02,
     "pickup_time": "2026-03-10T08:00:00", "delivery_deadline": "2026-03-12T18:00:00",
     "priority": (i % 5) + 1, "status": "pending"}
    for i in range(50)
]
DEMO_VEHICLES = [
    {"vehicle_id": f"veh-{j:02d}", "vehicle_type": "truck", "capacity_weight": 15000, "capacity_volume": 60.0,
     "cost_per_km": 15.0, "fuel_efficiency": 8.0, "co2_per_km": 0.9, "availability_status": True}
    for j in range(15)
]
DEMO_CLUSTERS = [
    {"cluster_id": f"clust-{k}", "shipment_ids": [f"ship-{k*3:03d}", f"ship-{k*3+1:03d}"],
     "cluster_weight": 2000 + k * 200, "cluster_volume": 10 + k}
    for k in range(8)
]


def main():
    agent = DQNAgent(
        epsilon=1.0,
        epsilon_decay=0.99,
        num_episodes=200,
        checkpoint_path="./checkpoints/dqn_logistics.pth"
    )
    logger.info("Starting DQN training...")
    history = agent.train(
        shipments=DEMO_SHIPMENTS,
        vehicles=DEMO_VEHICLES,
        clusters=DEMO_CLUSTERS,
        num_episodes=200
    )
    logger.info(f"Training complete. Final history: {history[-1] if history else 'N/A'}")
    with open("training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    logger.info("Saved training_history.json")


if __name__ == "__main__":
    main()
