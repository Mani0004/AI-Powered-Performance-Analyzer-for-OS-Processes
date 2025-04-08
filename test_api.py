import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key found: {'Yes' if api_key else 'No'}")

try:
    # Set API key
    openai.api_key = api_key
    
    # Test API call
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Hello, this is a test message."}
        ]
    )
    
    # Print response
    print("\nAPI Test Result:")
    print("Success! API is working correctly.")
    print(f"Response: {response['choices'][0]['message']['content']}")
    
except Exception as e:
    print("\nAPI Test Result:")
    print(f"Error: {str(e)}")