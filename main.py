# main.py
import asyncio
import config
from pipeline import run_localization_pipeline

async def main():
    print("🚀 Початок роботи системи локалізації відео...")
    # Тут можна додати логіку вибору мови через input()
    await run_localization_pipeline(config.VIDEO_FILE, target_lang="en")

if __name__ == "__main__":
    asyncio.run(main())