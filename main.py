# main.py
from game import Game

if __name__ == "__main__":
    print("Starting Werewolf LLM Game...")
    
    num_players = 0
    while num_players < 3 or num_players > 10: # Min 3 players for 1W,1S,1V. Max 10 for sanity.
        try:
            num_players_str = input("Enter number of players (e.g., 3-10): ")
            num_players = int(num_players_str)
            if num_players < 3:
                print("Minimum 3 players required.")
            if num_players > 10: # Arbitrary upper limit for this simple version
                print("Maximum 10 players for this version. For more, role distribution needs adjustment.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    llm_model_name = input(f"Enter Ollama model name (default 'llama3', e.g., 'mistral', 'codellama'): ")
    if not llm_model_name.strip():
        llm_model_name = "llama3"
    
    try:
        game_instance = Game(num_players=num_players, llm_model=llm_model_name)
        game_instance.run_game()
    except Exception as e:
        print(f"\nAn error occurred during game initialization or execution: {e}")
        print("Please ensure Ollama is running and the specified model is available.")
        import traceback
        traceback.print_exc()

    print("\nGame finished.")