# llm_interface.py
import ollama
import re

class LLMInterface:
    def __init__(self, model_name="llama3"):
        self.model_name = model_name
        print(f"LLMInterface initialized with model: {self.model_name}")
        try:
            # Check if the model is available
            ollama.list() 
        except Exception as e:
            print(f"Error: Could not connect to Ollama or list models. Is Ollama running?")
            print(f"Details: {e}")
            print(f"Make sure you have run 'ollama pull {self.model_name}' if it's your first time.")
            raise

    def _get_response(self, prompt_text):
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt_text}]
            )
            return response['message']['content'].strip()
        except Exception as e:
            print(f"Error communicating with Ollama model {self.model_name}: {e}")
            return "Error: Could not get a response."

    def get_player_choice(self, prompt_text, player_names_options):
        """
        Gets a choice from the LLM, expecting one of the player_names_options.
        Retries a few times if the response is not one of the options.
        """
        full_prompt = f"{prompt_text}\nChoose one name from this list: {', '.join(player_names_options)}. Respond with only the player's name."
        
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            raw_response = self._get_response(full_prompt)
            print(f"LLM raw choice response: {raw_response}")
            
            # Try to find any of the player names in the response
            for name in player_names_options:
                if re.search(r'\b' + re.escape(name) + r'\b', raw_response, re.IGNORECASE):
                    return name
            
            print(f"LLM did not provide a valid player name. Attempt {attempts+1}/{max_attempts}.")
            attempts += 1
        
        print(f"LLM failed to provide a valid player name after {max_attempts} attempts. Defaulting.")
        # Fallback: pick a random valid option if LLM fails consistently
        import random
        return random.choice(player_names_options)


    def get_player_statement(self, prompt_text):
        """Gets a general statement from the LLM."""
        full_prompt = f"{prompt_text}\nKeep your statement concise, ideally one or two sentences."
        return self._get_response(full_prompt)