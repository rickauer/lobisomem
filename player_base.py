# player_base.py
from llm_interface import LLMInterface

class Player:
    def __init__(self, name: str, llm_interface: LLMInterface):
        self.name = name
        self.role = self.__class__.__name__ # Villager, Werewolf, Seer
        self.is_alive = True
        self.llm_interface = llm_interface
        self.known_information = [] # List of strings, e.g., "PlayerX is a Werewolf"

    def __str__(self):
        return f"{self.name} ({self.role}{', Dead' if not self.is_alive else ''})"

    def get_game_state_summary(self, players, daytime_discussion=None):
        """Creates a summary of the game state for the LLM."""
        alive_players = [p.name for p in players if p.is_alive]
        summary = f"You are {self.name}, a {self.role}.\n"
        summary += f"Your objective is to {'help the Villagers win by eliminating Werewolves' if self.role != 'Werewolf' else 'eliminate Villagers until your numbers are equal or greater'}.\n"
        summary += f"Players currently alive: {', '.join(alive_players)}.\n"
        
        if self.known_information:
            summary += "Information you know:\n"
            for info in self.known_information:
                summary += f"- {info}\n"
        
        if daytime_discussion:
            summary += "\nPrevious statements from today's discussion:\n"
            for speaker, statement in daytime_discussion:
                summary += f"- {speaker}: \"{statement}\"\n"
        return summary

    def night_action(self, players, game_log_callback):
        """Placeholder for night actions. Overridden by Werewolf and Seer."""
        pass # Villagers do nothing at night

    def daytime_statement(self, players, discussion_history):
        """LLM generates a statement for the day."""
        game_state = self.get_game_state_summary(players, daytime_discussion=discussion_history)
        prompt = (
            f"{game_state}\n"
            "It's daytime discussion. What do you want to say to the group? "
            "Consider your role and what you know. Be persuasive or deceptive as your role requires."
        )
        return self.llm_interface.get_player_statement(prompt)

    def vote(self, players, discussion_history):
        """LLM decides who to vote for lynching."""
        game_state = self.get_game_state_summary(players, daytime_discussion=discussion_history)
        
        # Filter out self from voting options if desired, or dead players
        vote_options = [p.name for p in players if p.is_alive and p.name != self.name]
        if not vote_options: # Should not happen if game is still running with >1 player
             # If only self is left, this shouldn't be called.
             # If only one other player is left, that's the only option.
            vote_options = [p.name for p in players if p.is_alive and p.name != self.name]
            if not vote_options and len([p for p in players if p.is_alive]) == 1: # Only self left
                return self.name # Or handle game end before this
            elif not vote_options : # Should not happen in a normal game state
                 print(f"Warning: No valid vote options for {self.name}")
                 return None


        prompt = (
            f"{game_state}\n"
            "It's time to vote for lynching. Based on the discussion and your knowledge, "
            f"who do you vote to lynch? Your role is {self.role}."
        )
        chosen_player_name = self.llm_interface.get_player_choice(prompt, vote_options)
        return chosen_player_name

    def add_known_info(self, info_string):
        if info_string not in self.known_information:
            self.known_information.append(info_string)