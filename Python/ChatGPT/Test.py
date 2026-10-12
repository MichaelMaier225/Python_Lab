from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Get the API key from the .env file
api_key = os.getenv("OPENAI_API_KEY")

# Print the API key (or an error if not found)
if api_key:
    print("API Key loaded successfully!")
else:
    print("Failed to load API Key. Check your .env file.")
