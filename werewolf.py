# werewolf_llm_game/werewolf.py
from player_base import Player
import random

class Werewolf(Player):
    def __init__(self, name, game_master=None): # Added game_master
        super().__init__(name, "Werewolf", game_master=game_master) # Pass to super
        self.game_knowledge["fellow_werewolves"] = [] 

    def night_action_prompt(self, game_master_unused): # game_master_unused
        alive_non_werewolves = [
            p.name for p in self.game_master.get_alive_players() # Use self.game_master
            if p.role_name_en != "Werewolf" 
        ]
        if not alive_non_werewolves:
            return "There are no valid targets left for Werewolves." 

        prompt = (
            f"You are a Werewolf. It is night. Choose a player to eliminate. "
            f"Your fellow Werewolves (alive) are: {', '.join(self.game_knowledge.get('fellow_werewolves', ['N/A'])) if self.game_knowledge.get('fellow_werewolves') else 'You are the only werewolf.'}\n"
            f"Alive players who are NOT WEREWOLVES: {', '.join(alive_non_werewolves)}.\n"
            f"Who do you choose to eliminate? Respond with ONLY the player's name."
        )
        return prompt

    def perform_night_action(self, game_master_unused, victim_name): # game_master_unused
        self.add_to_context(f"You and your fellow werewolves decided to attack {victim_name}.", role="assistant")