# game.py
import random
import time
from collections import Counter

from llm_interface import LLMInterface
from player_base import Player
from villager import Villager
from werewolf_player import Werewolf # Ensure this matches the filename werewolf_player.py
from seer import Seer


class Game:
    def __init__(self, num_players=5, llm_model="llama3"):
        if num_players < 3:
            raise ValueError("Game requires at least 3 players.")
        
        self.llm_interface = LLMInterface(model_name=llm_model)
        self.players = []
        self.num_players = num_players
        self.day_number = 0
        self.game_log = [] # To store major game events

        self._setup_players()

    def _log(self, message):
        print(message)
        self.game_log.append(message)

    def _setup_players(self):
        player_names = [f"Player{i+1}" for i in range(self.num_players)]
        random.shuffle(player_names)

        # Define roles: 1 Werewolf, 1 Seer, rest Villagers
        # This can be made more dynamic for larger games
        num_werewolves = 1
        num_seers = 1
        num_villagers = self.num_players - num_werewolves - num_seers

        if num_villagers < 0 : # e.g. 2 players, 1 wolf, 1 seer = 0 villagers. Min 3.
            # Adjust roles if not enough players for standard setup
            if self.num_players == 3: # 1 wolf, 1 seer, 1 villager
                num_villagers = 1
            else: # Should not happen with num_players >=3 check. But as fallback:
                num_villagers = max(0, num_villagers) # Ensure non-negative
                self._log("Warning: Role distribution might be unusual due to low player count.")


        roles = ([Werewolf] * num_werewolves +
                 [Seer] * num_seers +
                 [Villager] * num_villagers)
        
        random.shuffle(roles) # Shuffle roles to assign randomly

        for i in range(self.num_players):
            player_name = player_names[i]
            player_role_class = roles[i]
            self.players.append(player_role_class(player_name, self.llm_interface))
            # Do NOT reveal roles here, only to the player themselves (which is handled by their init)

        self._log("--- Game Setup ---")
        self._log(f"Players: {', '.join(p.name for p in self.players)}")
        # For debugging, you might want to see roles:
        # self._log(f"Assigned roles: {', '.join(str(p) for p in self.players)}") # STR reveals role
        self._log("Roles have been secretly assigned.")
        self._log("------------------")


    def _print_player_status(self):
        self._log("\nCurrent Player Status:")
        for player in self.players:
            status = "Alive" if player.is_alive else "Dead"
            # self._log(f"- {player.name} ({player.role}): {status}") # Reveals role
            self._log(f"- {player.name}: {status}") # Does not reveal role


    def _get_alive_players(self):
        return [p for p in self.players if p.is_alive]

    def _get_alive_werewolves(self):
        return [p for p in self.players if p.is_alive and p.role == "Werewolf"]

    def _get_alive_villagers_and_seer(self): # Town-aligned
        return [p for p in self.players if p.is_alive and p.role != "Werewolf"]

    def _check_game_over(self):
        alive_werewolves = self._get_alive_werewolves()
        alive_villagers_team = self._get_alive_villagers_and_seer()

        if not alive_werewolves:
            self._log("\n--- GAME OVER ---")
            self._log("All Werewolves have been eliminated! Villagers Win!")
            return True
        
        if len(alive_werewolves) >= len(alive_villagers_team):
            self._log("\n--- GAME OVER ---")
            self._log("Werewolves now equal or outnumber Villagers! Werewolves Win!")
            return True
            
        if not alive_villagers_team: # Should be caught by above, but good check
             self._log("\n--- GAME OVER ---")
             self._log("All Villagers have been eliminated! Werewolves Win!")
             return True

        return False

    def _night_phase(self):
        self.day_number += 1
        self._log(f"\n--- NIGHT {self.day_number} ---")
        self._log("Night falls. All players go to sleep...")
        time.sleep(1) # For dramatic effect

        # Store night actions results
        werewolf_target = None
        
        # Werewolves act
        # In a multi-wolf game, they'd need to coordinate or one acts for the pack
        # For now, assuming one wolf or they 'magically' agree (first wolf's choice)
        for player in self._get_alive_players():
            if player.role == "Werewolf":
                target = player.night_action(self._get_alive_players(), self._log)
                if target: # Werewolf might not choose if no valid targets
                    werewolf_target = target 
                break # Only one werewolf pack action for now

        # Seer acts (after werewolves, so they can't be saved by Seer finding them same night)
        for player in self._get_alive_players():
            if player.role == "Seer":
                player.night_action(self._get_alive_players(), self._log)
                break # Only one Seer action

        time.sleep(1)
        self._log("\n--- DAWN ---")
        # Resolve night actions
        if werewolf_target:
            if werewolf_target.is_alive: # Make sure target wasn't somehow protected/already dead
                werewolf_target.is_alive = False
                self._log(f"A new day dawns. Sadly, {werewolf_target.name} was killed during the night.")
            else: # This case should be rare if targeting logic is correct
                 self._log(f"A new day dawns. The werewolves attacked {werewolf_target.name}, but they were already dead.")

        else:
            self._log("A new day dawns. Miraculously, everyone survived the night!")
        
        self._print_player_status()


    def _day_phase(self):
        self._log(f"\n--- DAY {self.day_number} ---")
        if self._check_game_over(): return

        self._log("Players gather in the village square for discussion.")
        
        discussion_history = [] # list of (speaker_name, statement) tuples
        alive_players_today = self._get_alive_players() # Players alive at start of discussion
        
        # Each alive player makes a statement
        # Shuffle order of speaking for fairness
        speaker_order = random.sample(alive_players_today, len(alive_players_today))
        for player in speaker_order:
            if player.is_alive: # Double check, though list should only contain alive
                self._log(f"\nIt's {player.name}'s turn to speak.")
                time.sleep(0.5) # Pause for LLM
                statement = player.daytime_statement(self.players, discussion_history)
                self._log(f"{player.name} says: \"{statement}\"")
                discussion_history.append((player.name, statement))
                time.sleep(1) # Pause after statement

        self._log("\n--- VOTING ---")
        self._log("After the discussion, it's time to vote for who to lynch.")
        
        votes = Counter()
        voters = self._get_alive_players()
        for player in voters:
            if player.is_alive:
                self._log(f"\n{player.name}, who do you vote to lynch?")
                time.sleep(0.5)
                
                # Players cannot vote for themselves (handled in Player.vote by filtering options)
                # Ensure vote_options are only other alive players
                vote_options_names = [p.name for p in self.players if p.is_alive and p.name != player.name]
                
                if not vote_options_names:
                    self._log(f"{player.name} has no one to vote for (this shouldn't happen in a normal game).")
                    continue

                chosen_name = player.vote(self.players, discussion_history)
                
                if chosen_name:
                    # Validate the LLM choice against current alive players who are not self
                    valid_target = False
                    for p_target in self.players:
                        if p_target.name == chosen_name and p_target.is_alive and p_target.name != player.name:
                            valid_target = True
                            break
                    
                    if valid_target:
                        self._log(f"{player.name} votes for {chosen_name}.")
                        votes[chosen_name] += 1
                    else:
                        self._log(f"{player.name} tried to vote for {chosen_name}, which is not a valid target. Vote ignored.")
                else:
                    self._log(f"{player.name} abstained or failed to vote.")
                time.sleep(0.5)

        if not votes:
            self._log("No votes were cast. No one is lynched today.")
            return

        self._log("\nVote Tally:")
        for name, count in votes.most_common():
            self._log(f"- {name}: {count} vote(s)")

        # Determine lynched player (simple majority, ties = no lynch or random)
        # For simplicity: highest vote count is lynched. If tie for highest, no one is lynched.
        
        lynched_player_name = None
        if votes:
            top_votes = votes.most_common()
            if len(top_votes) == 1: # Only one person received votes
                lynched_player_name = top_votes[0][0]
            elif len(top_votes) > 1 and top_votes[0][1] > top_votes[1][1]: # Clear winner
                lynched_player_name = top_votes[0][0]
            else: # Tie for the highest vote
                self._log("There's a tie for the most votes! No one is lynched today.")


        if lynched_player_name:
            lynched_player = next((p for p in self.players if p.name == lynched_player_name), None)
            if lynched_player and lynched_player.is_alive:
                lynched_player.is_alive = False
                self._log(f"\nBy popular vote, {lynched_player.name} has been lynched!")
                self._log(f"{lynched_player.name} was a {lynched_player.role}.") # Reveal role on lynch
            elif lynched_player and not lynched_player.is_alive:
                 self._log(f"\n{lynched_player_name} was chosen, but was already dead.")
            else: # Should not happen
                 self._log(f"\nError: Lynched player {lynched_player_name} not found or issue with status.")

        self._print_player_status()


    def run_game(self):
        self._log("Let the game of Werewolf begin!")
        
        # Initial role reveal to each player (handled by their knowledge)
        for player in self.players:
            player.add_known_info(f"You are a {player.role}.")
            if player.role == "Werewolf":
                 # Tell werewolves who other werewolves are (if any)
                 other_wolves = [w.name for w in self._get_alive_werewolves() if w.name != player.name]
                 if other_wolves:
                     player.add_known_info(f"Your fellow werewolf(s): {', '.join(other_wolves)}.")
                 else:
                     player.add_known_info("You are the only werewolf.")


        while not self._check_game_over():
            self._night_phase()
            if self._check_game_over(): break
            self._day_phase()
            if self._check_game_over(): break
            
            # Safety break for very long games / testing
            if self.day_number > 20: 
                self._log("Game has gone on for too long, ending.")
                break
        
        self._log("\n--- FINAL PLAYER ROLES ---")
        for player in self.players:
            self._log(f"{player.name} was a {player.role}.")
        
        self._log("\n--- GAME LOG ---")
        for entry in self.game_log:
            print(entry) # Print again for consolidated view if needed, or write to file