# werewolf_llm_game/seer.py
from player_base import Player

class Seer(Player):
    def __init__(self, name, game_master=None): # Added game_master
        super().__init__(name, "Seer", game_master=game_master) # Pass to super
        self.game_knowledge["known_werewolves_at_start"] = [] 

    def night_action_prompt(self, game_master_unused): # game_master_unused
        alive_players_to_investigate = [
            p.name for p in self.game_master.get_alive_players() if p.name != self.name # Use self.game_master
        ]
        if not alive_players_to_investigate:
            return "There are no other living players to investigate."

        prompt = (
            f"You are the Seer. It is night. Choose a player to investigate and discover their role.\n"
            f"Remember, at the start of the game you were told the Werewolves were: {', '.join(self.game_knowledge.get('known_werewolves_at_start', ['N/A']))}.\n"
            f"Alive players (excluding yourself): {', '.join(alive_players_to_investigate)}.\n"
            f"Who do you choose to investigate? Respond with ONLY the player's name."
        )
        return prompt

    def perform_night_action(self, game_master_unused, investigated_player_name): # game_master_unused
        target_player = self.game_master._get_player_by_name(investigated_player_name) # Use self.game_master
        if target_player:
            role_revealed = target_player.role_name_display 
            message_to_seer = f"You investigated {investigated_player_name} and discovered their role is: {role_revealed}."
            self.add_to_context(message_to_seer, role="game_master_info")
            # GM will log the actual result separately in game.py's night_phase
        else:
            self.add_to_context(f"You tried to investigate {investigated_player_name}, but that person was not found.", role="game_master_info")