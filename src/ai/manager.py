import os
import subprocess
from pathlib import Path
from typing import Dict

BOTS_DIR = Path("temp_bots")

class BotManager:
    """
    Manages the lifecycle of running bot subprocesses.
    This class is designed as a singleton, instantiated once and shared.
    """
    def __init__(self):
        self.running_processes: Dict[str, subprocess.Popen] = {}
        BOTS_DIR.mkdir(exist_ok=True)
        print("BotManager initialized.")

    async def deploy_bot(self, bot_id: str, bot_code: str, bot_token: str):
        """
        Saves the bot's code to a file and starts it in a new subprocess.
        """
        if bot_id in self.running_processes:
            # If the bot is already running, stop it before deploying the new version.
            await self.stop_bot(bot_id)

        bot_dir = BOTS_DIR / bot_id
        bot_dir.mkdir(exist_ok=True)

        bot_file_path = bot_dir / "bot.py"
        with open(bot_file_path, 'w') as f:
            f.write(bot_code)

        # Prepare the environment for the subprocess, adding the bot's token.
        env = os.environ.copy()
        env['BOT_TOKEN'] = bot_token
        
        # For python-telegram-bot, we might need to ensure the library is found.
        # Adding the project's src to PYTHONPATH can help in some environments.
        env['PYTHONPATH'] = os.getenv('PYTHONPATH', '') + ':' + os.path.abspath('src')

        print(f"Deploying bot {bot_id}...")
        process = subprocess.Popen(
            ['python', str(bot_file_path)],
            cwd=str(bot_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.running_processes[bot_id] = process
        print(f"Bot {bot_id} deployed with PID: {process.pid}")

    async def stop_bot(self, bot_id: str):
        """
        Terminates a running bot's subprocess.
        """
        if bot_id in self.running_processes:
            process = self.running_processes[bot_id]
            print(f"Stopping bot {bot_id} with PID: {process.pid}...")
            process.terminate()
            try:
                # Wait briefly for the process to terminate gracefully
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If it doesn't terminate, force kill it
                print(f"Bot {bot_id} did not terminate gracefully, killing.")
                process.kill()
            
            del self.running_processes[bot_id]
            print(f"Bot {bot_id} stopped.")
        else:
            print(f"Bot {bot_id} is not running.")

# Create a single instance of the manager to be used throughout the application
bot_manager = BotManager()
