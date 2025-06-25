import os
import subprocess
from pathlib import Path
import signal

BOTS_DIR = Path("temp_bots")

class BotManager:
    def __init__(self):
        BOTS_DIR.mkdir(exist_ok=True)
        print("BotManager initialized.")

    async def deploy_bot(self, bot_id: str, bot_code: str, bot_token: str) -> int:
        bot_dir = BOTS_DIR / bot_id
        bot_dir.mkdir(exist_ok=True)

        bot_file_path = bot_dir / "bot.py"
        with open(bot_file_path, 'w') as f:
            f.write(bot_code)

        env = os.environ.copy()
        env['BOT_TOKEN'] = bot_token
        
        env['PYTHONPATH'] = os.getenv('PYTHONPATH', '') + ':' + os.path.abspath('src')

        print(f"Deploying bot {bot_id}...")
        process = subprocess.Popen(
            ['python', '-u', 'bot.py'],
            cwd=str(bot_dir),
            env=env
        )
        print(f"Bot {bot_id} deployed with PID: {process.pid}")
        return process.pid

    async def stop_bot(self, pid: int):
        if pid:
            print(f"Stopping bot with PID: {pid}...")
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Bot with PID {pid} terminated.")
            except ProcessLookupError:
                print(f"Bot with PID {pid} was not found. It might have already stopped.")
            except Exception as e:
                print(f"An error occurred while stopping PID {pid}: {e}")
        else:
            print("No PID found for this bot, can't stop.")

bot_manager = BotManager()
