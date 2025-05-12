# werewolf_llm_game/game.py
import random
import time
from collections import Counter
import os 
import datetime 

from player_base import Player, OLLAMA_MODEL, OLLAMA_TEMPERATURE
from villager import Villager
from werewolf import Werewolf
from seer import Seer
from doctor import Doctor

LOG_DIRECTORY = "log"

class GameMaster:
    def __init__(self, player_names, num_werewolves=1, include_seer=True, include_doctor=True, speech_limit_per_day=None):
        self.player_names = player_names
        self.num_players = len(player_names)
        self.num_werewolves_start = num_werewolves
        self.include_seer = include_seer
        self.include_doctor = include_doctor
        
        if speech_limit_per_day is None:
            self.speech_limit_per_day = self.num_players * 2 
        else:
            self.speech_limit_per_day = speech_limit_per_day

        self.players = [] 
        self.player_map = {} 
        self.day_number = 0
        self.game_over = False
        self.winner = None 
        self.night_actions = {}
        
        self.game_log = [] 
        self.log_file_path = None
        self._setup_logging()

    def _setup_logging(self):
        if not os.path.exists(LOG_DIRECTORY):
            try:
                os.makedirs(LOG_DIRECTORY)
            except OSError as e:
                print(f"Error creating log directory {LOG_DIRECTORY}: {e}")
                # Fallback: Log to current directory if log dir creation fails
                self.log_file_path = f"werewolf_game_fallback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                self._log_event(f"Warning: Could not create log directory. Logging to {self.log_file_path}")
                return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(LOG_DIRECTORY, f"werewolf_game_{timestamp}.txt")
        self._log_event(f"Game log started at {datetime.datetime.now()}")
        self._log_event(f"Players: {', '.join(self.player_names)}")
        self._log_event(f"Roles Config: WW:{self.num_werewolves_start}, Seer:{self.include_seer}, Doctor:{self.include_doctor}")
        self._log_event(f"Speech Limit Per Day: {self.speech_limit_per_day}")
        self._log_event(f"LLM Model: {OLLAMA_MODEL}, Temperature: {OLLAMA_TEMPERATURE}")

    def _log_event(self, message):
        print(message) 
        self.game_log.append(str(message)) # Ensure message is string

    def _log_llm_interaction(self, player_name, system_prompt, context_history_str, user_prompt, llm_response):
        # context_history_str is already prepared by call_ollama
        log_message_parts = [
            # f"\n--- [LLM Call for {player_name} in Log] ---",
            # f"System: {system_prompt}",
            # str(context_history_str), # Use the prepared string
            # f"User: {user_prompt}",
            # f"LLM Raw Response: {llm_response}",
            # f"--- [End LLM Call for {player_name} in Log] ---\n"
        ]
        for line in log_message_parts:
            self.game_log.append(line)

    def _write_log_to_file(self):
        if self.log_file_path:
            try:
                with open(self.log_file_path, "w", encoding="utf-8") as f:
                    for line in self.game_log:
                        f.write(line + "\n")
                print(f"\nGame log saved to: {self.log_file_path}")
            except Exception as e:
                print(f"Error writing log file {self.log_file_path}: {e}")
        else:
            print("Error: Log file path was not set. Log not saved.")

    def _get_player_by_name(self, name):
        return self.player_map.get(name)

    def get_alive_players(self, role_filter=None):
        alive = [p for p in self.players if p.is_alive]
        if role_filter:
            roles_to_check = [role_filter] if isinstance(role_filter, str) else role_filter
            return [p for p in alive if p.role_name_en in roles_to_check]
        return alive

    def get_alive_player_names(self, role_filter=None):
        return [p.name for p in self.get_alive_players(role_filter=role_filter)]
    
    def _update_player_counts(self):
        self.werewolves_alive_count = len(self.get_alive_players("Werewolf"))
        self.villagers_team_alive_count = len(self.get_alive_players(["Villager", "Seer", "Doctor"]))
        self._log_event(f"[GM INFO] Counts updated: WW: {self.werewolves_alive_count}, Village Team: {self.villagers_team_alive_count}")

    def _broadcast_message(self, message, to_roles=None, to_specific_players=None, exclude_players=None):
        self._log_event(f"[GM BROADCAST TO ALL RELEVANT] {message}") 
        
        target_players_obj = []
        if to_specific_players:
            for name in to_specific_players:
                player = self._get_player_by_name(name)
                if player:
                    target_players_obj.append(player)
        elif to_roles:
            roles_to_target = [to_roles] if isinstance(to_roles, str) else to_roles
            for player in self.players: 
                if player.role_name_en in roles_to_target: 
                    target_players_obj.append(player)
        else: 
            target_players_obj = self.get_alive_players()

        excluded_player_objs = []
        if exclude_players:
            for name in exclude_players:
                player = self._get_player_by_name(name)
                if player:
                    excluded_player_objs.append(player)

        for player in target_players_obj:
            if player not in excluded_player_objs:
                player.add_to_context(message, role="game_master_info")

    def setup_game(self):
        self._log_event("--- SETTING UP THE GAME ---")
        if self.num_players < 3:
            self._log_event("Error: Insufficient number of players.")
            return False
        
        num_special_roles = self.num_werewolves_start
        if self.include_seer:
            num_special_roles += 1
        if self.include_doctor:
            num_special_roles += 1

        if num_special_roles > self.num_players:
            self._log_event("Error: More special roles than players.")
            return False

        roles_to_assign = []
        roles_to_assign.extend(["Werewolf"] * self.num_werewolves_start)
        if self.include_seer:
            roles_to_assign.append("Seer")
        if self.include_doctor:
            roles_to_assign.append("Doctor")
        
        num_villagers = self.num_players - len(roles_to_assign)
        if num_villagers < 0:
            self._log_event("Error: Villager calculation resulted in a negative number. Check role configuration.")
            return False
        roles_to_assign.extend(["Villager"] * num_villagers)

        random.shuffle(roles_to_assign)
        
        temp_player_list = list(self.player_names) 
        random.shuffle(temp_player_list)

        for i, name in enumerate(temp_player_list):
            role_en = roles_to_assign[i] 
            player = None
            # Pass self (GameMaster instance) to player constructors for logging
            if role_en == "Werewolf":
                player = Werewolf(name, game_master=self) 
            elif role_en == "Seer":
                player = Seer(name, game_master=self)
            elif role_en == "Doctor":
                player = Doctor(name, game_master=self)
            else: 
                player = Villager(name, game_master=self)
            
            self.players.append(player)
            self.player_map[name] = player
            self._log_event(f"[GM SECRET] Player {name} assigned as {player.role_name_display}")

        all_player_names_str = ", ".join(self.player_names)
        general_rules_prompt = (
            f"Welcome to the game of Werewolf, {{player_name}}!\n"
            f"Game Objective: Villagers win if they eliminate all Werewolves. Werewolves win if their number equals or exceeds the number of Villagers team members.\n"
            f"The game alternates between Day and Night phases.\n"
            f"Players in this game: {all_player_names_str}.\n"
            f"Daytime Communication Rules: You will speak in turns. There's a limit to speeches per day. When you speak, indicate who speaks next ('[Name]' or 'anyone').\n"
            f"Voting Rules (End of Day, Optional): After discussion, players will decide if there's a vote. If yes, secret nominations occur, then a secret vote. Ties result in no elimination.\n"
            f"Special Roles: Roles like Werewolf, Seer, Doctor exist. Their abilities are used at night.\n"
            f"Your secret role in this game is: {{player_role}}."
        )

        werewolf_names = [p.name for p in self.players if p.role_name_en == "Werewolf"]

        for player in self.players:
            player.add_to_context(general_rules_prompt.format(player_name=player.name, player_role=player.role_name_display), role="system")

            if player.role_name_en == "Werewolf":
                fellow_ww = [name for name in werewolf_names if name != player.name]
                player.game_knowledge["fellow_werewolves"] = fellow_ww
                if fellow_ww:
                    player.add_to_context(f"You are a Werewolf. Your fellow werewolves are: {', '.join(fellow_ww)}.", role="system")
                else:
                    player.add_to_context("You are a Werewolf and currently the only one of your kind.", role="system")
            
            if player.role_name_en == "Seer":
                player.game_knowledge["known_werewolves_at_start"] = list(werewolf_names) 
                player.add_to_context(f"You are the Seer. ALL Werewolves in this game are: {', '.join(werewolf_names) if werewolf_names else 'None (this should not happen in a standard game)'}.", role="system")
        
        self._update_player_counts() 
        self.day_number = 1
        self._log_event("--- GAME SETUP COMPLETE ---")
        return True

    def _check_game_over(self):
        # _update_player_counts() is called at start of day and after death, so counts should be fresh
        # but call again for safety if this method is used standalone.
        # self._update_player_counts() 
        
        if self.werewolves_alive_count == 0:
            if not self.game_over: # Ensure win condition is announced only once
                self.game_over = True
                self.winner = "Villagers"
                self._broadcast_message("All werewolves have been eliminated! VILLAGERS WIN!")
            return True
        
        if self.werewolves_alive_count >= self.villagers_team_alive_count:
            if not self.game_over: # Ensure win condition is announced only once
                self.game_over = True
                self.winner = "Werewolves"
                self._broadcast_message("The Werewolves have taken over the village! WEREWOLVES WIN!")
            return True
        
        return False

    def _handle_player_death(self, player_name, cause_of_death=""):
        player = self._get_player_by_name(player_name)
        if player and player.is_alive:
            player.is_alive = False
            self._broadcast_message(f"{player.name} ({player.role_name_display}) has died {cause_of_death}.")
            # self._log_event(f"[GM EVENT] {player.name} ({player.role_name_display}) died.") # Broadcast already logs this.
            self._update_player_counts() 
            return True
        return False

    def day_phase(self):
        self._log_event(f"\n--- DAY {self.day_number} ---")
        self._broadcast_message(f"Good morning, Village! Day {self.day_number} begins.")

        if self.day_number > 1:
            victim_name = self.night_actions.get("victim_of_night")
            saved_by_doctor = self.night_actions.get("was_saved_by_doctor", False)

            if victim_name and not saved_by_doctor:
                self._broadcast_message(f"During the night, the werewolves attacked. Unfortunately, {victim_name} did not survive.")
                self._handle_player_death(victim_name, "attacked by werewolves")
                if self._check_game_over(): return 
            elif victim_name and saved_by_doctor:
                self._broadcast_message("The werewolves claimed a victim last night, but someone intervened. No one was found dead this morning.")
            elif self.werewolves_alive_count > 0 and not victim_name: # Check if WWs active but no victim was set
                 self._broadcast_message("The night was quiet, and no one was attacked by werewolves.")
            elif self.werewolves_alive_count == 0: # No WWs left to attack
                self._broadcast_message("The night was peaceful as no werewolves remain.")
            else: # Other edge cases
                self._broadcast_message("The night was strangely calm.")


        alive_player_names = self.get_alive_player_names()
        self._broadcast_message(f"Alive players ({len(alive_player_names)}): {', '.join(alive_player_names) if alive_player_names else 'Nobody'}.")

        if self._check_game_over(): return # Check win condition after night's events and before discussion

        self._broadcast_message(f"Today's discussion will have a limit of {self.speech_limit_per_day} speeches. Let the deliberations begin!")
        
        speeches_made = 0
        current_speaker_player = random.choice(self.get_alive_players()) if self.get_alive_players() else None
        
        while speeches_made < self.speech_limit_per_day and current_speaker_player and len(self.get_alive_players()) > 0 :
            if not current_speaker_player.is_alive: 
                available_speakers = self.get_alive_players()
                if not available_speakers: break
                current_speaker_player = random.choice(available_speakers)

            self._log_event(f"\n{current_speaker_player.name}'s turn to speak ({self.speech_limit_per_day - speeches_made} speeches remaining)...")
            
            options_for_next = [p_name for p_name in self.get_alive_player_names() if p_name != current_speaker_player.name]

            speech, next_speaker_name_indicated = current_speaker_player.get_speech_and_next_speaker(
                self, 
                self.speech_limit_per_day - speeches_made,
                options_for_next 
            )
            
            speeches_made += 1
            speech_record = f"[{speeches_made}/{self.speech_limit_per_day}] {current_speaker_player.name}: '{speech}' (Indicated next: {next_speaker_name_indicated})"
            # self._log_event(f"[GM LOG OF SPEECH] {speech_record}") # Logged by broadcast
            self._broadcast_message(speech_record) # Broadcast the speech to all players

            if next_speaker_name_indicated == "anyone" or not self._get_player_by_name(next_speaker_name_indicated):
                available_next_speakers = [p for p in self.get_alive_players() if p != current_speaker_player]
                if not available_next_speakers: break 
                current_speaker_player = random.choice(available_next_speakers)
            else:
                next_speaker_candidate = self._get_player_by_name(next_speaker_name_indicated)
                if next_speaker_candidate and next_speaker_candidate.is_alive:
                    current_speaker_player = next_speaker_candidate
                else: 
                    available_next_speakers = [p for p in self.get_alive_players() if p != current_speaker_player]
                    if not available_next_speakers: break
                    current_speaker_player = random.choice(available_next_speakers)
            
            time.sleep(0.1) # Short delay

        self._broadcast_message("The day's discussion has ended.")

        if not self.get_alive_players(): 
            return

        votes_for_elimination_round = 0
        self._log_event("\n--- DECISION TO VOTE ---")
        for player in self.get_alive_players():
            time.sleep(0.1)
            self._log_event(f"Asking {player.name} if they want a vote...")
            response = player.get_yes_no_response(
                "The discussion has ended. Do you want to hold a vote to eliminate someone today? (Answer YES or NO)"
            )
            self._log_event(f"[GM RECORD] {player.name} responded '{response}' to holding a vote.")
            if response == "YES":
                votes_for_elimination_round += 1
            player.add_to_context(f"You voted '{response}' on whether to hold an elimination vote.", role="game_master_info")

        if votes_for_elimination_round > len(self.get_alive_players()) / 2:
            self._broadcast_message("The majority has decided to hold a vote. Let's proceed to nominations.")
            self._handle_lynch_vote()
        else:
            self._broadcast_message("The village has decided not to hold a vote today. Night approaches.")
        
        if self._check_game_over(): return

    def _handle_lynch_vote(self):
        self._log_event("\n--- LYNCH VOTE ---")
        alive_players = self.get_alive_players()
        if len(alive_players) < 2 : 
            self._broadcast_message("Not enough players for an effective vote.")
            return

        nominations = [] 
        for player in alive_players:
            time.sleep(0.1)
            nomination_options = [p.name for p in alive_players if p.name != player.name]
            if not nomination_options:
                player.add_to_context("There is no one else to nominate.", role="game_master_info")
                self._log_event(f"{player.name} had no one to nominate.")
                continue

            self._log_event(f"Asking {player.name} for a nomination...")
            chosen_nominee = player.get_player_choice_from_list(
                "Who would you like to nominate for possible elimination?",
                nomination_options,
                allow_abstain=True, 
                abstain_option="Abstain from nominating"
            )
            self._log_event(f"[GM RECORD] {player.name} nominated '{chosen_nominee}'.")
            if chosen_nominee and chosen_nominee not in ["Abstain from nominating", None]:
                nominations.append(chosen_nominee)
                player.add_to_context(f"You nominated {chosen_nominee} for elimination.", role="game_master_info")
            else:
                player.add_to_context("You abstained from nominating.", role="game_master_info")

        if not nominations:
            self._broadcast_message("No one was nominated for elimination. Night approaches.")
            return

        nomination_counts = Counter(nominations)
        nominated_players_distinct = list(nomination_counts.keys())
        self._broadcast_message(f"Players nominated for elimination: {', '.join(nominated_players_distinct)}. Now for the final vote.")

        final_votes = [] 
        for player in alive_players:
            time.sleep(0.1)
            self._log_event(f"Asking {player.name} for their final vote...")
            vote_choice = player.get_player_choice_from_list(
                f"Vote for one of the nominated players to eliminate: {', '.join(nominated_players_distinct)}. Or abstain.",
                nominated_players_distinct,
                allow_abstain=True,
                abstain_option="Abstain from voting"
            )
            self._log_event(f"[GM RECORD] {player.name} voted to eliminate '{vote_choice}'.")
            if vote_choice and vote_choice not in ["Abstain from voting", None]:
                final_votes.append(vote_choice)
                player.add_to_context(f"You voted to eliminate {vote_choice}.", role="game_master_info")
            else:
                player.add_to_context("You abstained in the final vote.", role="game_master_info")
        
        if not final_votes:
            self._broadcast_message("No one received votes in the final ballot. Nobody is eliminated. Night approaches.")
            return

        vote_counts = Counter(final_votes)
        most_votes = 0
        eliminated_player_name = None
        tied = False

        if vote_counts:
            max_v = max(vote_counts.values())
            players_with_max_v = [p_name for p_name, count in vote_counts.items() if count == max_v]
            if len(players_with_max_v) == 1:
                eliminated_player_name = players_with_max_v[0]
                most_votes = max_v
            else:
                tied = True 

        if tied or not eliminated_player_name: 
            self._broadcast_message(f"The vote ended in a tie or with no decisive votes. No one was eliminated today. Night approaches.")
        else:
            eliminated_player_obj = self._get_player_by_name(eliminated_player_name)
            self._broadcast_message(f"The vote has concluded. With {most_votes} votes, {eliminated_player_name} has been eliminated by the village.")
            
            self._handle_player_death(eliminated_player_name, "eliminated by the village")
            
            if eliminated_player_obj.role_name_en == "Werewolf": 
                if self._check_game_over(): return 
            if not self.game_over:
                 self._broadcast_message("With the decision made, night falls...")

    def night_phase(self):
        if self.game_over: return
        self._log_event(f"\n--- NIGHT {self.day_number} ---")
        self._broadcast_message("Night has fallen upon the village. Everyone goes to sleep... except those with nightly business.")
        
        self.night_actions = { 
            "werewolf_target": None, "seer_target": None, "doctor_target": None,
            "victim_of_night": None, "was_saved_by_doctor": False
        }
        
        alive_werewolves = self.get_alive_players("Werewolf")
        alive_non_werewolves = [p for p in self.get_alive_players() if p.role_name_en != "Werewolf"]
        
        werewolf_chosen_target = None
        if alive_werewolves and alive_non_werewolves:
            self._broadcast_message("The werewolves gather to choose a victim...", to_roles="Werewolf")
            werewolf_votes = []
            for ww_player in alive_werewolves:
                time.sleep(0.1)
                self._log_event(f"Asking Werewolf {ww_player.name} for a target...")
                prompt_for_ww = ww_player.night_action_prompt(self)
                if "no valid targets" in prompt_for_ww.lower(): 
                    ww_player.add_to_context(prompt_for_ww, role="game_master_info")
                    self._log_event(f"Werewolf {ww_player.name}: {prompt_for_ww}")
                    continue
                target_options = [p.name for p in alive_non_werewolves]
                chosen_victim = ww_player.get_player_choice_from_list(prompt_for_ww, target_options)
                self._log_event(f"[GM RECORD] Werewolf {ww_player.name} chose to attack '{chosen_victim}'.")
                if chosen_victim and chosen_victim in target_options:
                    werewolf_votes.append(chosen_victim)
                    ww_player.add_to_context(f"You voted to attack {chosen_victim}.", role="assistant")
                else: 
                    fallback_victim = random.choice(target_options) if target_options else None
                    if fallback_victim:
                        werewolf_votes.append(fallback_victim)
                        ww_player.add_to_context(f"You did not make a clear choice, so a random target ({fallback_victim}) was considered for your vote.", role="game_master_info")
                        self._log_event(f"[GM FALLBACK] Werewolf {ww_player.name} assigned random target {fallback_victim}.")
                    else:
                        self._log_event(f"[GM INFO] Werewolf {ww_player.name} had no valid targets for fallback.")


            if werewolf_votes:
                vote_counts = Counter(werewolf_votes)
                most_common_vote = vote_counts.most_common(1)
                if most_common_vote: werewolf_chosen_target = most_common_vote[0][0]
                
                if werewolf_chosen_target:
                    self.night_actions["werewolf_target"] = werewolf_chosen_target
                    self._broadcast_message(f"The werewolves have decided to attack: {werewolf_chosen_target}.", to_roles="Werewolf")
                else: self._broadcast_message("The werewolves could not decide on a target.", to_roles="Werewolf")
            else: self._broadcast_message("The werewolves did not choose a target tonight.", to_roles="Werewolf")
        elif alive_werewolves and not alive_non_werewolves:
            self._broadcast_message("There are no non-werewolves left for the werewolves to attack.", to_roles="Werewolf")

        seer_player = next((p for p in self.get_alive_players("Seer")), None)
        if seer_player:
            time.sleep(0.1)
            self._log_event(f"Asking Seer {seer_player.name} to investigate...")
            prompt_for_seer = seer_player.night_action_prompt(self)
            if "no other living players" in prompt_for_seer.lower(): 
                seer_player.add_to_context(prompt_for_seer, role="game_master_info")
                self._log_event(f"Seer {seer_player.name}: {prompt_for_seer}")
            else:
                target_options = [p.name for p in self.get_alive_players() if p.name != seer_player.name]
                if target_options:
                    chosen_to_investigate = seer_player.get_player_choice_from_list(prompt_for_seer, target_options)
                    self._log_event(f"[GM RECORD] Seer {seer_player.name} chose to investigate '{chosen_to_investigate}'.")
                    if chosen_to_investigate and chosen_to_investigate in target_options:
                        self.night_actions["seer_target"] = chosen_to_investigate
                        seer_player.perform_night_action(self, chosen_to_investigate) 
                        target_player_for_seer = self._get_player_by_name(chosen_to_investigate)
                        if target_player_for_seer:
                             self._log_event(f"[GM INFO] Seer {seer_player.name} found {target_player_for_seer.name} is a {target_player_for_seer.role_name_display}.")
                    else: 
                         seer_player.add_to_context("You did not make a clear choice for investigation.", role="game_master_info")
                         self._log_event(f"[GM INFO] Seer {seer_player.name} did not make a clear choice.")
                else:
                    seer_player.add_to_context("There was no one to investigate.", role="game_master_info")
                    self._log_event(f"Seer {seer_player.name} had no one to investigate.")

        doctor_player = next((p for p in self.get_alive_players("Doctor")), None)
        if doctor_player:
            time.sleep(0.1)
            self._log_event(f"Asking Doctor {doctor_player.name} to protect...")
            prompt_for_doctor = doctor_player.night_action_prompt(self)
            target_options = self.get_alive_player_names()
            if target_options:
                chosen_to_protect = doctor_player.get_player_choice_from_list(prompt_for_doctor, target_options)
                self._log_event(f"[GM RECORD] Doctor {doctor_player.name} chose to protect '{chosen_to_protect}'.")
                if chosen_to_protect and chosen_to_protect in target_options:
                    self.night_actions["doctor_target"] = chosen_to_protect
                    doctor_player.perform_night_action(self, chosen_to_protect)
                else: 
                    doctor_player.add_to_context("You did not make a clear choice for protection.", role="game_master_info")
                    self._log_event(f"[GM INFO] Doctor {doctor_player.name} did not make a clear choice.")
            else:
                doctor_player.add_to_context("There was no one to protect.", role="game_master_info")
                self._log_event(f"Doctor {doctor_player.name} had no one to protect.")

        ww_target = self.night_actions.get("werewolf_target")
        doc_target = self.night_actions.get("doctor_target")
        if ww_target:
            self.night_actions["victim_of_night"] = ww_target 
            if ww_target == doc_target:
                self.night_actions["was_saved_by_doctor"] = True
                self._log_event(f"[GM INFO] {ww_target} was attacked by werewolves, BUT SAVED by the Doctor!")
            else:
                self._log_event(f"[GM INFO] {ww_target} was attacked by werewolves. Doctor protected {doc_target if doc_target else 'nobody/other'}.")
        
        self._log_event(f"--- END OF NIGHT {self.day_number} ---")
        self.day_number += 1

    def run_game(self):
        if not self.setup_game():
            self._log_event("Failed to start game.")
            self._write_log_to_file() 
            return

        self._broadcast_message("The game has begun!") 
        
        while not self.game_over:
            self._update_player_counts() # Ensure counts are fresh at start of cycle
            if self._check_game_over(): # Check if game ended due to night events before day starts
                break
            self.day_phase()
            if self.game_over: break
            self.night_phase() 
            if self.game_over: break
            time.sleep(0.5) # Small pause between full night/day cycles

        self._log_event("\n--- GAME OVER ---")
        if self.winner:
            self._log_event(f"Winner(s): {self.winner}")
        else:
            # This can happen if all players die simultaneously or if game is interrupted.
            self._log_event("The game ended without a clear winner (or was interrupted).") 
        
        self._log_event("\n--- Final Role Summary ---")
        for player in self.players:
            self._log_event(f"{player.name} was a {player.role_name_display} and is {player.get_status()}.")
        
        self._write_log_to_file()

if __name__ == "__main__":
    PLAYER_NAMES = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "George", "Harry"] 
    NUM_WEREWOLVES = 2
    INCLUDE_SEER = True
    INCLUDE_DOCTOR = True
    SPEECH_LIMIT = len(PLAYER_NAMES) 
        
    gm = GameMaster(
        player_names=PLAYER_NAMES,
        num_werewolves=NUM_WEREWOLVES,
        include_seer=INCLUDE_SEER,
        include_doctor=INCLUDE_DOCTOR,
        speech_limit_per_day=SPEECH_LIMIT 
    )
    # Initial config is logged by GameMaster's __init__ via _setup_logging

    confirmation = input("This may take time and make many LLM calls. Continue? (y/n): ")
    if confirmation.lower() != 'y':
        gm._log_event("Game cancelled by user before starting.") 
        gm._write_log_to_file()
        print("Game cancelled.") 
    else:
        gm.run_game()