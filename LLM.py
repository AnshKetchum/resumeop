# OpenAI Compatible APIs
import openai

# ChatUI
from chatgpt_selenium_automation.handler.chatgpt_selenium_automation import ChatGPTAutomation
from webdriver_manager.chrome import ChromeDriverManager


class OpenAIBackendAPI:
    """
    A rough API that can serve as a backend for 
    any API that implements OpenAI's v1 standards.

    Notably, that would include:
        - GPT4all (CPU + GPU)
        - LocalAI (CPU + GPU w/ optimization)
        - vLLM (GPU only)
    """

    def __init__(self, openai_backend_url=openai.base_url, openai_model="gpt-3.5-turbo-1106"):
        self.history = []
        self.openai_backend_url = openai_backend_url
        self.openai_model = openai_model

    def generate(self) -> str:
        """
        Gets an OpenAI response from the current history of messages 
        """

        response = openai.chat.completions.create(
            model=self.openai_model,
            messages=self.history,
            temperature=0.7,
            presence_penalty=0,
            frequency_penalty=0.1
        )

        generated_texts = [
            choice.message.content.strip() for choice in response.choices
        ]

        return generated_texts[0]

    def add_human_prompt(self, human_prompt: str):
        self.add_message("system", human_prompt)

    def prompt_and_response(self, prompt: str):
        self.add_message("system", prompt)

        # Generate a response
        response = self.generate()

        # Add the response in
        self.add_message("assistant", response)
        return response

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def messages(self):
        return self.history

    def quit(self):
        pass


class OpenAIChatAPI:
    """
    An API that directly interfaces with the Chat UI OpenAI has (chat.openai.com) to 
    send and receive messages. Zero API costs, nada yadda yadda.

    Use this for small interactions (Resumes only)!
    """

    def __init__(self, chrome_path="/usr/bin/google-chrome"):
        self.history = []

        # Setup our automation
        chrome_driver_path = ChromeDriverManager().install()
        self.chatgpt = ChatGPTAutomation(chrome_path, chrome_driver_path)

        # Track the last prompt sent
        self.last_human_prompt = ""

    def generate(self) -> str:
        """
        Gets an OpenAI response from the current history of messages 
        """
        self.chatgpt.send_prompt_to_chatgpt(
            self.last_human_prompt.strip())

        response = self.chatgpt.return_last_response()
        return response

    def set_latest_human_prompt(self, human_prompt: str):
        self.last_human_prompt = human_prompt

    def add_human_prompt(self, human_prompt: str):

        self.set_latest_human_prompt(human_prompt)
        self.add_message("system", human_prompt)

    def prompt_and_response(self, prompt: str, add=True):
        self.add_message("system", prompt)

        self.set_latest_human_prompt(prompt)

        # Generate a response
        response = self.generate().strip("ChatGPT").strip()

        # Add the response in
        if add:
            self.add_message("assistant", response)
        return response

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def messages(self):
        return self.history

    def quit(self):
        self.chatgpt.quit()
