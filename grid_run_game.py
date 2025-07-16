import os
import csv
import datetime
import itertools
from game import GameMaster, LOG_DIRECTORY

# --- Grid Search Configuration ---
# A list of player names to be used in all game simulations.
PLAYER_NAMES = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "George", "Harry"]

# The number of times each unique game configuration will be executed.
EXECUTIONS_PER_CONFIG = 3

# --- Grid Search Parameters ---
# Defines the range for the number of werewolves to test. range(1, 4) means [1, 2, 3].
WEREWOLF_COUNTS = range(1, 4)

# Defines the options for including a Seer role.
SEER_OPTIONS = [True, False]

# Defines the options for including a Doctor role.
DOCTOR_OPTIONS = [True, False]


def run_grid_search():
    """
    Executes a grid search of the Werewolf game, iterating through all combinations
    of the defined parameters. It records the results of each game in a CSV file.
    """
    # Ensure the log directory exists.
    if not os.path.exists(LOG_DIRECTORY):
        try:
            os.makedirs(LOG_DIRECTORY)
        except OSError as e:
            print(f"Error creating log directory {LOG_DIRECTORY}: {e}")
            return

    # Create a unique filename for the results CSV based on the current timestamp.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_filename = os.path.join(LOG_DIRECTORY, f"grid_search_results_{timestamp}.csv")

    # Generate all unique combinations of game parameters.
    all_combinations = list(itertools.product(WEREWOLF_COUNTS, SEER_OPTIONS, DOCTOR_OPTIONS))
    total_runs = len(all_combinations) * EXECUTIONS_PER_CONFIG
    current_run = 0

    print(f"Starting grid search. Total game simulations to run: {total_runs}")
    print(f"Results will be saved to: {results_filename}")

    # Open the CSV file to write the results.
    with open(results_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write the header row for the CSV file.
        header = ["num_werewolves", "include_seer", "include_doctor", "execution_id", "winner", "total_days"]
        csv_writer.writerow(header)

        # Iterate through each combination of parameters.
        for num_ww, has_seer, has_doctor in all_combinations:
            
            print("\n" + "="*60)
            print(f"--- New Configuration: Werewolves={num_ww}, Seer={has_seer}, Doctor={has_doctor} ---")
            print("="*60)

            # Run the game N times for the current configuration.
            for i in range(EXECUTIONS_PER_CONFIG):
                current_run += 1
                execution_id = i + 1
                
                print(f"\n--> Running Execution {execution_id}/{EXECUTIONS_PER_CONFIG} for this config. (Overall Progress: {current_run}/{total_runs})")

                # Validate the configuration to ensure there are enough players for the assigned roles.
                num_special_roles = num_ww
                if has_seer: num_special_roles += 1
                if has_doctor: num_special_roles += 1
                
                if num_special_roles >= len(PLAYER_NAMES):
                    print(f"Skipping config: Too many special roles ({num_special_roles}) for {len(PLAYER_NAMES)} players.")
                    result_row = [num_ww, has_seer, has_doctor, execution_id, "SKIPPED_INVALID_CONFIG", 0]
                    csv_writer.writerow(result_row)
                    continue

                # Set a speech limit for the game day phase.
                speech_limit = len(PLAYER_NAMES)

                # Initialize the GameMaster with the current set of parameters.
                # Note: The game will print its full log to the console. This is expected.
                gm = GameMaster(
                    player_names=PLAYER_NAMES,
                    num_werewolves=num_ww,
                    include_seer=has_seer,
                    include_doctor=has_doctor,
                    speech_limit_per_day=speech_limit
                )
                
                # Run the game simulation.
                gm.run_game()

                # Retrieve the results from the game instance.
                winner = gm.winner if gm.winner else "No Winner"
                num_days = gm.day_number

                # Write the results of the simulation to the CSV file.
                result_row = [num_ww, has_seer, has_doctor, execution_id, winner, num_days]
                csv_writer.writerow(result_row)
                print(f"--> Execution {execution_id} Finished. Winner: {winner} (Game lasted {num_days} days)")

    print("\n" + "="*60)
    print(f"Grid search complete. All simulations finished.")
    print(f"Results have been saved to {results_filename}")
    print("="*60)

if __name__ == "__main__":
    # Confirmation prompt to prevent accidental long-running execution.
    try:
        confirmation = input("This will start a grid search, which may take a very long time and make many LLM calls. Continue? (y/n): ")
        if confirmation.lower().strip() == 'y':
            run_grid_search()
        else:
            print("Grid search cancelled by user.")
    except KeyboardInterrupt:
        print("\nGrid search interrupted by user. Exiting.")