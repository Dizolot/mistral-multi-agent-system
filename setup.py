from setuptools import setup, find_packages

setup(
    name="telegram_bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot",
        "aiohttp",
        "python-dotenv"
    ]
) 