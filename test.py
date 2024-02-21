from chatgpt_selenium_automation.handler.chatgpt_selenium_automation import ChatGPTAutomation
from webdriver_manager.chrome import ChromeDriverManager

# Define the path where the chrome driver is installed on your computer
chrome_driver_path = ChromeDriverManager().install()

# the sintax r'"..."' is required because the space in "Program Files" in the chrome path
chrome_path = '/usr/bin/google-chrome'

# Create an instance
chatgpt = ChatGPTAutomation(chrome_path, chrome_driver_path)

# Define a prompt and send it to chatgpt
prompt = "What are the benefits of exercise?"
chatgpt.send_prompt_to_chatgpt(prompt)

# Retrieve the last response from ChatGPT
response = chatgpt.return_last_response()

print(response)

# Save the conversation to a text file
file_name = "conversation.txt"
chatgpt.save_conversation(file_name)

# Close the browser and terminate the WebDriver session
chatgpt.quit()
