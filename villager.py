# werewolf_llm_game/villager.py
from player_base import Player

class Villager(Player):
    def __init__(self, name, game_master=None): # Added game_master
        super().__init__(name, "Villager", game_master=game_master) # Pass to super
        # Villagers don't get special knowledge initially beyond their role