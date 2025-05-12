# werewolf_llm_game/doctor.py
from player_base import Player

class Doctor(Player):
    def __init__(self, name, game_master=None): # Added game_master
        super().__init__(name, "Doctor", game_master=game_master) # Pass to super

    def night_action_prompt(self, game_master_unused): # game_master_unused
        alive_players_to_protect = [p.name for p in self.game_master.get_alive_players()] # Use self.game_master
        if not alive_players_to_protect:
            return "There is no one to protect (this should not happen)."

        prompt = (
            f"You are the Doctor. It is night. Choose a player to protect from the werewolves' attack (this can be yourself).\n"
            f"Alive players: {', '.join(alive_players_to_protect)}.\n"
            f"Who do you choose to protect? Respond with ONLY the player's name."
        )
        return prompt

    def perform_night_action(self, game_master_unused, protected_player_name): # game_master_unused
        self.add_to_context(f"You chose to protect {protected_player_name} tonight.", role="assistant")