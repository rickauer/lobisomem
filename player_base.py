# werewolf_llm_game/player_base.py
import ollama
import random
import re

# --- Ollama Configuration ---
OLLAMA_MODEL = "magistral" # Or "llama3", "mistral", "orca-mini", etc.
OLLAMA_TEMPERATURE = 0.2 # Lower temperature for less randomness, more focused responses

# --- LLM Interaction Function ---
def call_ollama(system_prompt, user_prompt, context_history=None, player_name_for_log="Player", game_master_logger=None):
    """
    Calls the Ollama API, handles responses with <think> blocks, and logs interactions.
    """
    if context_history is None:
        context_history = []

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(context_history)
    messages.append({"role": "user", "content": user_prompt})

    max_retries = 3
    llm_response_content = f"Error: LLM call failed after {max_retries} attempts."
    for attempt in range(max_retries):
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                options={"temperature": OLLAMA_TEMPERATURE}
            )
            llm_response_content = response['message']['content'].strip()
            break
        except Exception as e:
            print(f"Error calling Ollama for {player_name_for_log} (Attempt {attempt + 1}/{max_retries}): {e}")
            llm_response_content = f"Error: Could not get response from LLM. Last error: {e}"
            if attempt == max_retries - 1:
                break

    # --- Response Parsing for <think> blocks ---
    thought_process = ""
    final_response = llm_response_content

    think_match = re.search(r"<think>(.*?)</think>", llm_response_content, re.DOTALL)
    if think_match:
        thought_process = think_match.group(1).strip()
        # The final response is everything outside the <think> block
        final_response = re.sub(r"<think>.*?</think>", "", llm_response_content, flags=re.DOTALL).strip()

    # --- Logging ---
    if game_master_logger:
        # Log the (potentially private) thought process
        if thought_process and hasattr(game_master_logger, '_log_player_thinking'):
            game_master_logger._log_player_thinking(player_name_for_log, thought_process)

        # Log the public-facing interaction
        if hasattr(game_master_logger, '_log_llm_interaction'):
            context_history_str = [str(msg) for msg in context_history]
            if len(context_history_str) > 4:
                logged_context = f"Context (last {min(len(context_history_str), 2)}): {context_history_str[-min(len(context_history_str),2):]}"
            else:
                logged_context = f"Context: {context_history_str}"
            
            game_master_logger._log_llm_interaction(
                player_name_for_log, system_prompt, logged_context, user_prompt, final_response
            )
            
    return final_response


class Player:
    def __init__(self, name, role_name, game_master=None): # Added game_master
        self.name = name
        self.role_name_en = role_name 
        self.role_name_display = role_name 
        
        self.is_alive = True
        self.context_history = [] 
        self.game_knowledge = {"role": self.role_name_en}
        self.game_master = game_master # Store game_master instance

    def __str__(self):
        return f"{self.name} ({self.role_name_display})"

    def get_status(self):
        return "Alive" if self.is_alive else "Dead"

    def add_to_context(self, message, role="user"):
        if role == "game_master_info":
             self.context_history.append({"role": "user", "content": f"[GM Update]: {message}"})
        else:
            self.context_history.append({"role": role, "content": message})
        MAX_CONTEXT_MSGS = 1000
        if len(self.context_history) > MAX_CONTEXT_MSGS:
            self.context_history = self.context_history[-MAX_CONTEXT_MSGS:]

    def get_llm_response(self, system_prompt, user_prompt):
        # Pass the game_master instance to call_ollama for logging
        return call_ollama(system_prompt, user_prompt, self.context_history, self.name, game_master_logger=self.game_master)

    def get_player_choice_from_list(self, prompt_instruction, choices, allow_abstain=False, abstain_option="Abstain"):
        choice_text = ", ".join(choices)
        full_prompt = (
            f"{prompt_instruction}\n"
            f"Your options are: {choice_text}.\n"
        )
        if allow_abstain:
            full_prompt += f"You can also choose to '{abstain_option}'.\n"
        full_prompt += "You can use the <think> tag to reason about your choice. This will not be seen by other players. Then, respond with ONLY the name of your choice from the list, or the abstain option if available. Nothing else."

        system_p = f"You are {self.name}, playing Werewolf. Your role is {self.role_name_display}. Follow instructions precisely. Provide only the requested choice."

        response_text = self.get_llm_response(system_p, full_prompt)
        
        self.add_to_context(full_prompt, role="user") 
        self.add_to_context(response_text, role="assistant")
        
        # --- NOVA VERIFICAÇÃO DE ROBUSTEZ ---
        # Se a resposta for muito longa para uma simples escolha, considere-a inválida.
        MAX_CHOICE_LENGTH = 100 
        if len(response_text) > MAX_CHOICE_LENGTH:
            if self.game_master: self.game_master._log_event(f"[GM Fallback] {self.name}'s response was too long and likely corrupt. Picking randomly.")
            if choices:
                return random.choice(choices)
            return None # Ou a opção de abster-se, se aplicável

        cleaned_response = response_text.strip() 

        for choice in choices:
            if choice.lower() == cleaned_response.lower():
                return choice
        if allow_abstain and abstain_option.lower() == cleaned_response.lower():
            return abstain_option
        
        for choice in choices:
            if re.search(r'\b' + re.escape(choice) + r'\b', response_text, re.IGNORECASE):
                if self.game_master: self.game_master._log_event(f"[GM Warning] {self.name} made a verbose choice for '{prompt_instruction}', but '{choice}' was found in '{response_text}'.")
                return choice
        if allow_abstain and re.search(r'\b' + re.escape(abstain_option) + r'\b', response_text, re.IGNORECASE):
            if self.game_master: self.game_master._log_event(f"[GM Warning] {self.name} made a verbose choice for '{prompt_instruction}', but '{abstain_option}' was found in '{response_text}'.")
            return abstain_option
        
        if self.game_master: self.game_master._log_event(f"[GM Fallback] {self.name} failed to make a clear choice ('{response_text}') for '{prompt_instruction}'. Picking randomly from valid options (excluding abstain).")
        if choices:
            return random.choice(choices)
        elif allow_abstain:
             return abstain_option
        return None

    def get_yes_no_response(self, prompt_instruction):
        full_prompt = (
            f"{prompt_instruction}\n"
            f"You can use the <think> tag to reason about your choice. This will not be seen by other players. Please answer with ONLY 'YES' or 'NO'. Nothing else."
        )
        system_p = f"You are {self.name}, playing Werewolf. Your role is {self.role_name_display}. Respond concisely with ONLY 'YES' or 'NO'."
        
        response_text = self.get_llm_response(system_p, full_prompt)

        self.add_to_context(full_prompt, role="user")
        self.add_to_context(response_text, role="assistant")

        cleaned_response = response_text.strip().upper()
        if cleaned_response == "YES":
            return "YES"
        elif cleaned_response == "NO":
            return "NO"
        
        if re.search(r'\bYES\b', response_text, re.IGNORECASE) or re.search(r'\bSIM\b', response_text, re.IGNORECASE):
            if self.game_master: self.game_master._log_event(f"[GM Warning] {self.name} response '{response_text}' for '{prompt_instruction}' parsed as YES.")
            return "YES"
        elif re.search(r'\bNO\b', response_text, re.IGNORECASE) or re.search(r'\bNÃO\b', response_text, re.IGNORECASE):
            if self.game_master: self.game_master._log_event(f"[GM Warning] {self.name} response '{response_text}' for '{prompt_instruction}' parsed as NO.")
            return "NO"
        
        if self.game_master: self.game_master._log_event(f"[GM Fallback] {self.name} failed to give a clear YES/NO ('{response_text}') for '{prompt_instruction}'. Defaulting to NO.")
        return "NO"

    def get_speech_and_next_speaker(self, game_master_unused, remaining_speeches, alive_player_names): # game_master_unused as self.game_master is now available
        options_next = alive_player_names + ["anyone"]
        prompt = (
            f"It's your turn to speak, {self.name}. There are {remaining_speeches} speeches left in today's discussion.\n"
            f"What do you say? Try to be persuasive or deflect suspicion, according to your role ({self.role_name_display}).\n"
            f"You can use the <think> tag to reason about your choice. This will not be seen by other players. After your speech, indicate who should speak next. The options are: {', '.join(options_next)}.\n"
            f"Your response MUST follow this EXACT format: MY SPEECH: [your speech here] NEXT: [player name or 'anyone']"
        )
        system_p = (
            f"You are {self.name}, a player in a game of Werewolf. Your secret role is {self.role_name_display}. "
            f"Remember your team's goal (Villagers want to eliminate Werewolves; Werewolves want to outnumber Villagers). "
            f"Be strategic in your speech. Follow the output format precisely."
        )
        
        response_text = self.get_llm_response(system_p, prompt) # This will use self.game_master for logging
        self.add_to_context(prompt, role="user")
        self.add_to_context(response_text, role="assistant")

        speech = response_text 
        next_speaker_name = "anyone" 

        match = re.search(r"MY SPEECH:\s*(.*?)\s*NEXT:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if match:
            speech = match.group(1).strip()
            next_speaker_str = match.group(2).strip()
            
            for name_option in alive_player_names: 
                if re.search(r'\b' + re.escape(name_option) + r'\b', next_speaker_str, re.IGNORECASE):
                    next_speaker_name = name_option
                    break
            else: 
                if "anyone" in next_speaker_str.lower() or "qualquer um" in next_speaker_str.lower(): 
                    next_speaker_name = "anyone"
                else:
                    potential_names = [p for p in alive_player_names if p.lower() in next_speaker_str.lower()]
                    if potential_names:
                        next_speaker_name = potential_names[0] 
                    else:
                        if self.game_master: self.game_master._log_event(f"[GM Warning] Could not determine next speaker from '{next_speaker_str}', defaulting to 'anyone'.")
                        next_speaker_name = "anyone" 
        else:
            if self.game_master: self.game_master._log_event(f"[GM Warning] Could not parse speech and next speaker from {self.name}'s response: '{response_text}'. Using full response as speech and 'anyone' as next.")
            speech = response_text # Usa a resposta inteira como fala por padrão
            next_speaker_name = "anyone" # Usa 'anyone' como próximo por padrão

            # Tenta encontrar uma indicação de próximo orador de forma mais robusta
            next_match = re.search(r"NEXT:\s*(\w+)", response_text, re.IGNORECASE)
            if next_match:
                potential_name = next_match.group(1)
                # Verifica se o nome encontrado está na lista de jogadores vivos
                for alive_name in alive_player_names:
                    if alive_name.lower() == potential_name.lower():
                        next_speaker_name = alive_name
                        # Remove a parte "NEXT..." da fala principal
                        speech = response_text[:next_match.start()].strip()
                        break
        return speech, next_speaker_name

    def night_action_prompt(self, game_master_unused): # game_master_unused
        return None 

    def perform_night_action(self, game_master_unused, choice_str): # game_master_unused
        pass