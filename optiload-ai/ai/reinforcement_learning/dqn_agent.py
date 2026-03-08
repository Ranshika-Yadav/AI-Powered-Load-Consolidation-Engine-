"""
Deep Q-Network (DQN) RL Agent for Logistics Optimization — OptiLoad AI
State: cluster features + fleet availability
Actions: merge, split, assign, delay
Reward: +utilization - cost - emissions - trips
"""
import os
import math
import json
import logging
import random
from collections import deque
from typing import List, Tuple, Dict

import numpy as np

logger = logging.getLogger(__name__)

# ── Try to import PyTorch; fall back to numpy mock if unavailable ─────────────
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. DQN will use random policy.")


# ── State / Action definitions ────────────────────────────────────────────────
STATE_DIM = 12   # [num_pending, num_clusters, avg_cluster_size, avg_utilization,
                 #  available_vehicles, avg_weight, avg_volume, max_weight, max_volume,
                 #  pending_high_priority, cluster_compatibility, fleet_load_factor]
ACTION_DIM = 4   # 0=merge_clusters, 1=split_cluster, 2=assign_vehicle, 3=delay_shipment

ACTIONS = ["merge_clusters", "split_cluster", "assign_vehicle", "delay_shipment"]


if TORCH_AVAILABLE:
    class DQNetwork(nn.Module):
        """Deep Q-Network architecture."""
        def __init__(self, state_dim: int = STATE_DIM, action_dim: int = ACTION_DIM, hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden, hidden // 2),
                nn.ReLU(),
                nn.Linear(hidden // 2, action_dim),
            )

        def forward(self, x):
            return self.net(x)
else:
    class DQNetwork:
        """Mock DQNetwork when PyTorch is unavailable."""
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, x):
            return np.random.rand(ACTION_DIM)


class ReplayBuffer:
    """Experience replay buffer."""
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        return random.sample(self.buffer, batch_size)

    def __len__(self):
        return len(self.buffer)


class LogisticsEnvironment:
    """
    Simplified logistics optimization environment.
    State features:
    - num_pending: number of pending shipments
    - num_clusters: number of current clusters
    - avg_cluster_size: mean shipments per cluster
    - avg_utilization: average vehicle utilization 0-1
    - available_vehicles: number of free vehicles
    - avg_weight: average shipment weight
    - avg_volume: average shipment volume
    - max_weight: max shipment weight
    - max_volume: max shipment volume
    - pending_high_priority: count of priority >= 4
    - cluster_compatibility: mean cluster compatibility score
    - fleet_load_factor: total load / total capacity
    """

    def __init__(self, shipments: List[dict], vehicles: List[dict], clusters: List[dict]):
        self.shipments = shipments
        self.vehicles = vehicles
        self.clusters = clusters
        self.step_count = 0
        self.max_steps = 50
        self.total_reward = 0.0
        self._compute_baseline()

    def _compute_baseline(self):
        """Compute baseline metrics for reward normalization."""
        self.baseline_utilization = 0.6  # 60% baseline
        self.baseline_cost = 100000.0    # baseline total cost
        self.baseline_co2 = 5000.0       # baseline CO2

    def _get_state(self) -> np.ndarray:
        """Encode current environment state as feature vector."""
        pending = [s for s in self.shipments if s.get("status") == "pending"]
        high_priority = sum(1 for s in pending if s.get("priority", 1) >= 4)
        
        total_cap_wt = sum(v.get("capacity_weight", 10000) for v in self.vehicles) or 1
        total_cap_vol = sum(v.get("capacity_volume", 50) for v in self.vehicles) or 1
        total_wt = sum(s.get("weight", 0) for s in pending)
        total_vol = sum(s.get("volume", 0) for s in pending)

        state = np.array([
            len(pending) / 200.0,                                    # normalized pending count
            len(self.clusters) / 50.0,                               # normalized cluster count
            (len(pending) / max(1, len(self.clusters))) / 10.0,      # avg cluster size
            self.baseline_utilization,                               # placeholder
            len(self.vehicles) / 50.0,                               # available vehicles ratio
            np.mean([s.get("weight", 0) for s in pending]) / 20000 if pending else 0,
            np.mean([s.get("volume", 0) for s in pending]) / 100 if pending else 0,
            max((s.get("weight", 0) for s in pending), default=0) / 50000,
            max((s.get("volume", 0) for s in pending), default=0) / 200,
            high_priority / max(1, len(pending)),                    # priority ratio
            0.6,                                                     # placeholder compatibility
            total_wt / total_cap_wt,                                 # fleet load factor
        ], dtype=np.float32)
        return state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """Execute action and compute reward."""
        self.step_count += 1
        reward = 0.0

        if action == 0:  # merge_clusters
            reward = self._action_merge()
        elif action == 1:  # split_cluster
            reward = self._action_split()
        elif action == 2:  # assign_vehicle
            reward = self._action_assign()
        elif action == 3:  # delay_shipment
            reward = self._action_delay()

        self.total_reward += reward
        done = self.step_count >= self.max_steps
        next_state = self._get_state()
        return next_state, reward, done

    def _action_merge(self) -> float:
        """Merge two small clusters — increases utilization."""
        small = [c for c in self.clusters if len(c.get("shipment_ids", [])) <= 3]
        if len(small) >= 2:
            # Simulate merge benefit
            return +2.5  # utilization improvement
        return -0.5  # no clusters to merge

    def _action_split(self) -> float:
        """Split oversized cluster — improves feasibility."""
        large = [c for c in self.clusters if
                 c.get("cluster_volume", 0) > 40]  # exceeds typical vehicle volume
        if large:
            return +1.0
        return -0.5

    def _action_assign(self) -> float:
        """Assign a cluster to best-fit vehicle — immediate cost saving."""
        if self.clusters and self.vehicles:
            return +3.0 - random.random()  # positive reward for assignment
        return -1.0

    def _action_delay(self) -> float:
        """Delay low-priority shipment to consolidate — risk of penalty."""
        low_prio = [s for s in self.shipments if s.get("priority", 1) <= 2 and s.get("status") == "pending"]
        if low_prio:
            return +0.5  # slight benefit from better consolidation
        return -2.0  # penalize unnecessary delays

    def reset(self):
        self.step_count = 0
        self.total_reward = 0.0
        return self._get_state()


class DQNAgent:
    """DQN agent with experience replay and target network."""

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
        lr: float = 1e-3,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        batch_size: int = 64,
        target_update_freq: int = 100,
        checkpoint_path: str = "/app/checkpoints/dqn_agent.pth",
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.checkpoint_path = checkpoint_path
        self.steps = 0
        self.replay_buffer = ReplayBuffer(capacity=20000)
        self.training_history: List[Dict] = []

        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.q_network = DQNetwork(state_dim, action_dim).to(self.device)
            self.target_network = DQNetwork(state_dim, action_dim).to(self.device)
            self.target_network.load_state_dict(self.q_network.state_dict())
            self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
            self.loss_fn = nn.MSELoss()
            self._load_checkpoint()
        else:
            self.device = None
            self.q_network = DQNetwork()
            self.target_network = DQNetwork()

    def _load_checkpoint(self):
        if TORCH_AVAILABLE and os.path.exists(self.checkpoint_path):
            try:
                checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
                self.q_network.load_state_dict(checkpoint["q_network"])
                self.target_network.load_state_dict(checkpoint["target_network"])
                self.epsilon = checkpoint.get("epsilon", self.epsilon)
                self.steps = checkpoint.get("steps", 0)
                logger.info(f"Loaded DQN checkpoint from {self.checkpoint_path}")
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")

    def save_checkpoint(self):
        if not TORCH_AVAILABLE:
            return
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        torch.save({
            "q_network": self.q_network.state_dict(),
            "target_network": self.target_network.state_dict(),
            "epsilon": self.epsilon,
            "steps": self.steps,
        }, self.checkpoint_path)
        logger.info(f"Saved DQN checkpoint to {self.checkpoint_path}")

    def select_action(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        if TORCH_AVAILABLE:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                q_values = self.q_network(state_tensor)
                return int(q_values.argmax().item())
        return random.randint(0, self.action_dim - 1)

    def update(self) -> Optional[float]:
        """Sample from replay buffer and update Q-network."""
        if not TORCH_AVAILABLE or len(self.replay_buffer) < self.batch_size:
            return None

        batch = self.replay_buffer.sample(self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states_t = torch.FloatTensor(np.array(states)).to(self.device)
        actions_t = torch.LongTensor(actions).to(self.device)
        rewards_t = torch.FloatTensor(rewards).to(self.device)
        next_states_t = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones_t = torch.FloatTensor(dones).to(self.device)

        # Current Q values
        q_values = self.q_network(states_t).gather(1, actions_t.unsqueeze(1)).squeeze(1)

        # Target Q values (Bellman equation)
        with torch.no_grad():
            next_q = self.target_network(next_states_t).max(1)[0]
            target_q = rewards_t + self.gamma * next_q * (1 - dones_t)

        loss = self.loss_fn(q_values, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()

        # Epsilon decay
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.steps += 1

        # Update target network
        if self.steps % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        return float(loss.item())

    def train(self, shipments: List[dict], vehicles: List[dict], clusters: List[dict],
              num_episodes: int = 200) -> List[Dict]:
        """Full training loop."""
        env = LogisticsEnvironment(shipments, vehicles, clusters)
        episode_rewards = []

        for episode in range(num_episodes):
            state = env.reset()
            total_reward = 0.0
            losses = []

            for step in range(env.max_steps):
                action = self.select_action(state)
                next_state, reward, done = env.step(action)
                self.replay_buffer.push(state, action, reward, next_state, done)
                loss = self.update()
                if loss:
                    losses.append(loss)
                state = next_state
                total_reward += reward
                if done:
                    break

            episode_rewards.append(total_reward)
            avg_loss = np.mean(losses) if losses else 0

            if (episode + 1) % 20 == 0:
                avg_reward = np.mean(episode_rewards[-20:])
                logger.info(f"Episode {episode+1}/{num_episodes} — Avg Reward: {avg_reward:.2f}, Loss: {avg_loss:.4f}, ε: {self.epsilon:.3f}")
                self.training_history.append({
                    "episode": episode + 1,
                    "avg_reward": round(avg_reward, 3),
                    "loss": round(avg_loss, 4),
                    "epsilon": round(self.epsilon, 3),
                })

        self.save_checkpoint()
        return self.training_history

    def get_recommendation(self, state: np.ndarray) -> Dict:
        """Get best action recommendation with confidence."""
        if TORCH_AVAILABLE:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                q_values = self.q_network(state_tensor).squeeze().cpu().numpy()
            best_action = int(np.argmax(q_values))
            confidence = float(np.exp(q_values[best_action]) / np.sum(np.exp(q_values)))
        else:
            best_action = random.randint(0, ACTION_DIM - 1)
            q_values = np.random.rand(ACTION_DIM)
            confidence = 0.25

        return {
            "recommended_action": ACTIONS[best_action],
            "action_index": best_action,
            "confidence": round(confidence, 3),
            "q_values": {ACTIONS[i]: round(float(q_values[i]), 3) for i in range(ACTION_DIM)},
        }
