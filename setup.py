from setuptools import setup, find_packages

setup(
    name="goose-tour-dates",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "discord.py==2.3.2",
        "selenium==4.18.1",
        "webdriver-manager==4.0.1",
        "python-dotenv==1.0.1",
        "requests==2.31.0",
        "beautifulsoup4==4.12.3",
        "jinja2",
        "colorama",
        "pandas",
        "geopy"
    ],
) 