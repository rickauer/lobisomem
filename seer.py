# seer.py
from player_base import Player
from llm_interface import LLMInterface

class Seer(Player):
    def __init__(self, name: str, llm_interface: LLMInterface):
        super().__init__(name, llm_interface)

    def night_action(self, players, game_log_callback):
        """Seer chooses a player to investigate."""
        game_log_callback(f"\nIt's {self.name}'s (Seer) turn to investigate.")
        game_state = self.get_game_state_summary(players)

        # Seer can investigate anyone alive, including themselves (though usually not optimal)
        # Cannot investigate dead players.
        investigate_options = [p.name for p in players if p.is_alive] # Can investigate self
        
        if not investigate_options:
            game_log_callback(f"{self.name} (Seer) has no one to investigate.")
            return # Nothing to do

        prompt = (
            f"{game_state}\n"
            "You are the Seer. It's night. Choose a player to investigate to learn their role (Werewolf or Not Werewolf). "
            "Your goal is to find the Werewolves."
        )
        
        chosen_player_name = self.llm_interface.get_player_choice(prompt, investigate_options)
        
        target_player = None
        for p in players:
            if p.name == chosen_player_name:
                target_player = p
                break
        
        if target_player:
            # For simplicity, Seer sees "Werewolf" or "Not Werewolf"
            # A more advanced Seer might see exact roles, or "good team" / "bad team"
            is_wolf = "is a Werewolf" if target_player.role == "Werewolf" else "is NOT a Werewolf"
            vision_result = f"Your vision reveals: {target_player.name} {is_wolf}."
            game_log_callback(f"{self.name} (Seer) investigated {target_player.name}. {vision_result} (Seer privately sees this)")
            self.add_known_info(f"{target_player.name} {is_wolf}.") # Add to Seer's private knowledge
        else:
            game_log_callback(f"{self.name} (Seer) failed to choose a valid player for investigation.")