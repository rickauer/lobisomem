# villager.py
from player_base import Player
from llm_interface import LLMInterface

class Villager(Player):
    def __init__(self, name: str, llm_interface: LLMInterface):
        super().__init__(name, llm_interface)
        # Villagers have no special night actions or starting info beyond their role