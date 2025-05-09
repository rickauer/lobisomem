# werewolf_player.py
from player_base import Player
from llm_interface import LLMInterface

class Werewolf(Player):
    def __init__(self, name: str, llm_interface: LLMInterface):
        super().__init__(name, llm_interface)
        # Werewolves might know other werewolves if we extend the game
        # For now, assumes one werewolf, so no special initial knowledge.

    def night_action(self, players, game_log_callback):
        """Werewolf chooses a player to kill."""
        game_log_callback(f"\nIt's {self.name}'s (Werewolf) turn to choose a victim.")
        
        game_state = self.get_game_state_summary(players)
        
        # Werewolves cannot kill themselves, or other werewolves (if multiple)
        # For now, just can't kill self. Can't kill already dead players.
        target_options = [p.name for p in players if p.is_alive and p.name != self.name and p.role != "Werewolf"] # Don't kill other wolves
        
        if not target_options:
            game_log_callback(f"{self.name} (Werewolf) has no valid targets.")
            return None # No one to kill

        prompt = (
            f"{game_state}\n"
            "You are a Werewolf. It's night. Choose a player to eliminate. "
            "Your goal is to reduce the number of villagers."
        )
        
        victim_name = self.llm_interface.get_player_choice(prompt, target_options)
        game_log_callback(f"{self.name} (Werewolf) has chosen to attack {victim_name}.")
        
        # Find the player object
        for player in players:
            if player.name == victim_name:
                return player
        return None # Should not happen if name is from target_options