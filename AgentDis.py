import os
import numpy as np
import torch as T
import torch.nn as nn
import torch.optim as optim
from torch.distributions.categorical import Categorical
from torch.utils.tensorboard import SummaryWriter
from torch.amp import GradScaler, autocast
import time
import random
import matplotlib.pyplot as plt


# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Create a unique log directory with timestamp
timestamp = time.strftime("%Y%m%d-%H%M%S")
log_dir = os.path.join('logs', f'agent_{timestamp}')
writer = SummaryWriter(log_dir=log_dir)



class PPOMemory:
    def __init__(self, batch_size):
        self.states = []
        self.log_probs = []
        self.vals = []
        self.actions = []
        self.rewards = []
        self.dones = []

        self.batch_size = batch_size

    def generate_batches(self):
        n_states = len(self.states)
        batch_start = np.arange(0, n_states, self.batch_size)
        indices = np.arange(n_states, dtype=np.int64)
        np.random.shuffle(indices)
        batches = [indices[i:i+self.batch_size] for i in batch_start]

        return np.array(self.states),\
                np.array(self.actions),\
                np.array(self.log_probs),\
                np.array(self.vals),\
                np.array(self.rewards),\
                np.array(self.dones),\
                batches

    def store_memory(self, state, action, log_prob, vals, reward, done):
        self.states.append(state)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.vals.append(vals)
        self.rewards.append(reward)
        self.dones.append(done)

    def clear_memory(self):
        self.states = []
        self.log_probs = []
        self.actions = []
        self.rewards = []
        self.dones = []
        self.vals = []

    def export_memory(self):
        return {
            "states": self.states,
            "log_probs": self.log_probs,
            "vals": self.vals,
            "actions": self.actions,
            "rewards": self.rewards,
            "dones": self.dones,
        }

    def import_memory(self, memory_data):
        self.states.extend(memory_data["states"])
        self.log_probs.extend(memory_data["log_probs"])
        self.vals.extend(memory_data["vals"])
        self.actions.extend(memory_data["actions"])
        self.rewards.extend(memory_data["rewards"])
        self.dones.extend(memory_data["dones"])

class ActorNetwork(nn.Module):
    def __init__(self, n_actions, input_dims, alpha, device, chkpt_dir='models'):
        super(ActorNetwork, self).__init__()
        
        # Create checkpoint directory if it doesn't exist
        os.makedirs(chkpt_dir, exist_ok=True)


        self.fc1_dims = 256
        self.fc2_dims = 256
        self.fc3_dims = 16
        #self.fc3_dims = 64
        #self.fc4_dims = 32
        #self.fc5_dims = 16
        #self.fc6_dims = 8

        self.checkpoint_file = os.path.join(chkpt_dir, 'actor')
        self.actor = nn.Sequential(
                nn.Linear(input_dims, self.fc1_dims),
                nn.ReLU(),
                nn.Linear(self.fc1_dims, self.fc2_dims),
                nn.ReLU(),
                nn.Linear(self.fc2_dims, self.fc3_dims),
                nn.ReLU(),
                nn.Linear(self.fc3_dims, n_actions)
        )

        self.optimizer = optim.Adam(self.parameters(), lr=alpha)
        self.device = device 
        self.to(self.device)

    def forward(self, state):
        logits = self.actor(state)
        dist = Categorical(logits=logits)
        
        return dist
        
    def get_logits(self, state):
        """Exportable forward method that returns logits only"""
        return self.actor(state)

    def save_checkpoint(self):
        T.save(self.state_dict(), self.checkpoint_file)

    def load_checkpoint(self):
        self.load_state_dict(T.load(self.checkpoint_file))

class CriticNetwork(nn.Module):
    def __init__(self, input_dims, alpha, device, chkpt_dir='models'):
        super(CriticNetwork, self).__init__()
        
        # Create checkpoint directory if it doesn't exist
        os.makedirs(chkpt_dir, exist_ok=True)

        self.fc1_dims = 256
        self.fc2_dims = 256
        self.fc3_dims = 16
        #self.fc3_dims = 64
        #self.fc4_dims = 32
        #self.fc5_dims = 16
        #self.fc6_dims = 8


        self.checkpoint_file = os.path.join(chkpt_dir, 'critic')
        self.critic = nn.Sequential(
                nn.Linear(input_dims, self.fc1_dims),
                nn.ReLU(),
                nn.Linear(self.fc1_dims, self.fc2_dims),
                nn.ReLU(),
                nn.Linear(self.fc2_dims, self.fc3_dims),
                nn.ReLU(),
                nn.Linear(self.fc3_dims, 1)
        )

        self.optimizer = optim.Adam(self.parameters(), lr=alpha)
        self.device = device
        self.to(self.device)

    def forward(self, state):
        value = self.critic(state)

        return value

    def save_checkpoint(self):
        T.save(self.state_dict(), self.checkpoint_file)

    def load_checkpoint(self):
        self.load_state_dict(T.load(self.checkpoint_file))

class AgentDis:
    def __init__(self, n_actions, input_dims, gamma=0.99, alpha=0.0001, gae_lambda=0.95,
            policy_clip=0.1, batch_size=128, n_epochs=3, max_grad_norm=0.5, seed=42, entropy_coef=0.001):
        # Set seeds for reproducibility

    #def __init__(self, n_actions, input_dims, gamma=0.99, alpha=0.0003, gae_lambda=0.95,
    #        policy_clip=0.2, batch_size=256, n_epochs=10, max_grad_norm=0.5, seed=42, entropy_coef=0.01):
        
        self.gamma = gamma
        self.policy_clip = policy_clip
        self.n_epochs = n_epochs
        self.gae_lambda = gae_lambda
        self.max_grad_norm = max_grad_norm
        self.learning_iteration = 0
        self.seed = seed
        self.entropy_coef = entropy_coef
        self.device = T.device('cpu')
        self.actor = ActorNetwork(n_actions, input_dims, alpha, self.device)
        self.critic = CriticNetwork(input_dims, alpha, self.device)
        self.memory = PPOMemory(batch_size)
        self.scaler = GradScaler() if self.device.type == 'cuda' else None

        if os.path.exists(f"models/actor"):
            self.load_models()
        else:
            self.save_models()
       
    def remember(self, state, action, probs, vals, reward, done):
        self.memory.store_memory(state, action, probs, vals, reward, done)

    def save_models(self):
        print(f'... saving models for agent ...')
        self.actor.save_checkpoint()
        self.critic.save_checkpoint()

    def load_models(self):
        print(f'... loading models for agent ...')
        self.actor.load_checkpoint()
        self.critic.load_checkpoint()

    def eval(self):
        self.actor.eval()
        self.critic.eval()

    def train(self):
        self.actor.train()
        self.critic.train()

    def choose_action(self, observation):
        # Convert observation to numpy array if it's not already
        if not isinstance(observation, np.ndarray):
            observation = np.array(observation, dtype=np.float32)
        
        # Create tensor from numpy array
        state = T.tensor(observation, dtype=T.float32, device=self.device).unsqueeze(0)


        # Fast path for evaluation mode
        if not self.actor.training:
            with T.inference_mode():  # More optimized than no_grad for inference
                with autocast(device_type=self.device.type, enabled=(self.device.type == 'cuda')):
                    logits = self.actor.actor(state)
                action = T.argmax(logits, dim=1).item()
            return action, None, None
        
        # Regular path for training mode
        with T.no_grad():
            with autocast(device_type=self.device.type, enabled=(self.device.type == 'cuda')):
                logits = self.actor.actor(state)
                value = self.critic(state).squeeze().item()
            dist = Categorical(logits=logits)
            action = dist.sample()
            log_prob = dist.log_prob(action).squeeze().item()
            action = action.item()
        
        return action, log_prob, value
    
    def learn(self, show_chart=False):
        self.train()
        
        running_loss = 0
        running_actor_loss = 0
        running_critic_loss = 0
        
        state_arr, action_arr, old_log_probs_arr, vals_arr, reward_arr, dones_arr, batches = \
            self.memory.generate_batches()
            
        # Show rewards chart if requested
        if show_chart:
            plt.figure(figsize=(12, 6))
            
            # Plot 1: Rewards over time
            plt.subplot(1, 2, 1)
            plt.plot(reward_arr, 'b-', alpha=0.7, linewidth=1)
            plt.title('Rewards Over Time')
            plt.xlabel('Step')
            plt.ylabel('Reward')
            plt.grid(True, alpha=0.3)
            
            # Plot 2: Reward distribution histogram
            plt.subplot(1, 2, 2)
            plt.hist(reward_arr, bins=30, alpha=0.7, color='green', edgecolor='black')
            plt.title('Reward Distribution')
            plt.xlabel('Reward Value')
            plt.ylabel('Frequency')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
            # Print reward statistics
            print(f"Reward Statistics:")
            print(f"  Mean: {np.mean(reward_arr):.4f}")
            print(f"  Std:  {np.std(reward_arr):.4f}")
            print(f"  Min:  {np.min(reward_arr):.4f}")
            print(f"  Max:  {np.max(reward_arr):.4f}")
            print(f"  Sum:  {np.sum(reward_arr):.4f}")
            
        states = T.tensor(state_arr, dtype=T.float32, device=self.device)
        rewards = T.tensor(reward_arr, dtype=T.float32, device=self.device)
        values = T.tensor(vals_arr, dtype=T.float32, device=self.device)
        dones = T.tensor(dones_arr, dtype=T.float32, device=self.device)

        # Calculate bootstrap value for non-terminal final state
        # Initialize last_value as a 0D scalar tensor
        last_value = T.tensor(0.0, dtype=T.float32, device=self.device)
        if len(dones) > 0 and not dones[-1]:
            last_state = T.tensor(state_arr[-1], dtype=T.float32, device=self.device).unsqueeze(0)
            with T.no_grad():
                last_value = self.critic(last_state).squeeze()  

        # Append bootstrap value for GAE
        values = T.cat((values, last_value.unsqueeze(0)))

        # Generalized Advantage Estimation
        advantages = T.zeros_like(rewards, device=self.device)
        gae = 0
        for t in reversed(range(len(rewards))):
            delta = rewards[t] + self.gamma * values[t + 1] * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages[t] = gae

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-5)

        for _ in range(self.n_epochs):
            for batch in batches:
                batch_states = T.tensor(state_arr[batch], dtype=T.float32, device=self.device)
                batch_actions = T.tensor(action_arr[batch], device=self.device)
                batch_old_log_probs = T.tensor(old_log_probs_arr[batch], device=self.device)
                batch_advantages = advantages[batch]
                batch_values = values[batch]
                
                # Zero gradients before autocast
                self.actor.optimizer.zero_grad()
                self.critic.optimizer.zero_grad()
                
                with autocast(device_type=self.device.type, enabled=(self.device.type == 'cuda')):
                    # Get logits from the actor network
                    logits = self.actor.actor(batch_states)
                    dist = Categorical(logits=logits)
                    critic_value = self.critic(batch_states).squeeze()

                    new_log_probs = dist.log_prob(batch_actions)
                    prob_ratio = (new_log_probs - batch_old_log_probs).exp()

                    # PPO update
                    unclipped = batch_advantages * prob_ratio
                    clipped = T.clamp(prob_ratio, 1 - self.policy_clip, 1 + self.policy_clip) * batch_advantages
                    actor_loss = -T.min(unclipped, clipped).mean()

                    # Entropy bonus
                    entropy = dist.entropy().mean()
                    entropy_bonus = self.entropy_coef * entropy
                    actor_loss -= entropy_bonus

                    critic_targets = batch_advantages + batch_values
                    critic_loss = (critic_targets - critic_value).pow(2).mean()

                    total_loss = actor_loss + 0.5 * critic_loss
                
                # Use scaler for backward pass
                if self.scaler:
                    self.scaler.scale(total_loss).backward()
                    # Clip gradients before optimizer step (after scaling back)
                    T.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
                    T.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
                    self.scaler.step(self.actor.optimizer)
                    self.scaler.step(self.critic.optimizer)
                    self.scaler.update()
                else:
                    total_loss.backward()
                    # Clip gradients
                    T.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
                    T.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
                    self.actor.optimizer.step()
                    self.critic.optimizer.step()

                running_loss += total_loss.item()
                running_actor_loss += actor_loss.item()
                running_critic_loss += critic_loss.item()

        # Calculate average losses
        n_updates = self.n_epochs * len(batches)
        avg_loss = running_loss / n_updates if n_updates > 0 else 0
        avg_actor_loss = running_actor_loss / n_updates if n_updates > 0 else 0
        avg_critic_loss = running_critic_loss / n_updates if n_updates > 0 else 0
        print(f"Avg Loss: {avg_loss}, Avg Actor Loss: {avg_actor_loss}, Avg Critic Loss: {avg_critic_loss}")

        # Log to TensorBoard
        writer.add_scalar(f'loss', avg_loss, self.learning_iteration)
        writer.add_scalar(f'actor_loss', avg_actor_loss, self.learning_iteration)
        writer.add_scalar(f'critic_loss', avg_critic_loss, self.learning_iteration)
        writer.flush()
        
        self.learning_iteration += 1
        self.memory.clear_memory()

    def export_models(self, export_dir='WOBT/Models'):
        """Exports the actor and critic models to TorchScript format (.pt) 
           which can be loaded by TorchSharp in C#.
        """
        os.makedirs(export_dir, exist_ok=True)
        
        print(f"Exporting TorchScript models to {export_dir}...")

        try:
            # Load the latest saved models first
            self.load_models() 

            # Ensure models are on CPU before scripting/saving for broader compatibility
            # (TorchSharp might load on CPU or GPU, CPU save is safer)
            actor_cpu = self.actor.cpu()
            critic_cpu = self.critic.cpu()
            
            # Set models to evaluation mode
            actor_cpu.eval()
            critic_cpu.eval()

            # Script the models. We script the inner sequential modules directly
            # as they contain the actual network graph.
            # Using torch.jit.script is preferred over trace for potential dynamicism 
            # and better compatibility with TorchSharp.
            # Note: The 'actor' and 'critic' attributes within ActorNetwork/CriticNetwork 
            # are the nn.Sequential modules.
            actor_script = T.jit.script(actor_cpu.actor)
            critic_script = T.jit.script(critic_cpu.critic)
            
            # Define save paths
            actor_path = os.path.join(export_dir, 'actor.pt') # Use .pt extension
            critic_path = os.path.join(export_dir, 'critic.pt') # Use .pt extension
            
            # Save the scripted models
            actor_script.save(actor_path)
            critic_script.save(critic_path)
            
            print(f"Actor model successfully exported to (TorchScript): {actor_path}")
            print(f"Critic model successfully exported to (TorchScript): {critic_path}")

            # Move models back to their original device if needed
            self.actor.to(self.device)
            self.critic.to(self.device)
            
            return actor_path, critic_path

        except Exception as e:
            print(f"Error during TorchScript model export: {e}")
            print("Ensure the models (ActorNetwork/CriticNetwork sequential parts) are compatible with torch.jit.script.")
            # Move models back to device even if export failed
            self.actor.to(self.device)
            self.critic.to(self.device)
            return None, None

    def get_state_dict(self):
        return {
            'actor_state_dict': self.actor.state_dict(),
            'critic_state_dict': self.critic.state_dict()
        }

    def load_state_dict(self, state_dict):
        self.actor.load_state_dict(state_dict['actor_state_dict'])
        self.critic.load_state_dict(state_dict['critic_state_dict'])



