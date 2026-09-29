from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, InternalServerError
import json
import os
import time
from pypdf import PdfReader
import gradio as gr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel
import os

load_dotenv(override=True)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
EVALUATOR_MODEL = os.getenv("GEMINI_EVALUATOR_MODEL", "gemini-3.1-flash-lite")

def with_retry(fn, attempts=4, base_delay=3):
    """Retry transient Gemini errors (rate limits / capacity spikes)."""
    for i in range(attempts):
        try:
            return fn()
        except (RateLimitError, InternalServerError) as e:
            if "PerDay" in str(e) or i == attempts - 1:
                raise
            time.sleep(base_delay * (i + 1))

def push(text, subject):
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("EMAIL_RECIPIENT")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 2525)) 
    smtp_login = os.getenv("SMTP_LOGIN", sender_email)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(text, "plain"))
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()  
            server.login(smtp_login, sender_password)
            server.send_message(message)
        return {"success": True}
    except Exception as e:
        print(f"Failed to send email: {e}")
        return {"success": False, "error": str(e)}


def record_user_details(email, name="Name not provided", notes="Not provided"):
    subject = f"New User Details Recorded: {name}"
    body = f"""
    A new user has been recorded with the following details:

    Name: {name}
    Email: {email}
    Notes: {notes}

    Please follow up with this user as needed.
    """
    result = push(body, subject)
    if not result["success"]:
        return {
            "recorded": "failed",
            "error": result["error"],
            "message": "Failed to send email. Please check the logs for details.",
        }
    return {"recorded": "ok"}

def record_unknown_question(question):
    subject = "Unknown Question Recorded"
    body = f"""
    An unknown question has been recorded:

    Question: {question}

    Please review this question and provide an appropriate response if possible.
    """
    result = push(body, subject)
    if not result["success"]:
        return {
            "recorded": "failed",
            "error": result["error"],
            "message": "Failed to send email. Please check the logs for details.",
        }
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]

class Evaluation(BaseModel):
    is_acceptable: bool
    feedback: str

class Me:

    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("GOOGLE_API_KEY"), base_url=GEMINI_BASE_URL)
        self.name = "Akiva Kaufman"
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        reader = PdfReader("me/resume.pdf")
        self.resume = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.resume += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background, resume and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website, and answer only in British English. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. \
If one of your tools fails, don't claim the action succeeded - apologise and ask the user to email directly instead. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n## Resume:\n{self.resume}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def evaluator_system_prompt(self):
        evaluator_system_prompt = f"You are an evaluator that decides whether a response to a question is acceptable. \
    You are provided with a conversation between a User and an Agent. Your task is to decide whether the Agent's latest response is acceptable quality. \
    The Agent is playing the role of {self.name} and is representing {self.name} on their website. \
    The Agent has been instructed to be professional and engaging, as if talking to a potential client or future employer who came across the website, and to use British English only. \
    The Agent has been provided with context on {self.name} in the form of their summary, resume and LinkedIn details. Here's the information:"

        evaluator_system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n## Resume:\n{self.resume}\n\n"
        evaluator_system_prompt += f"With this context, please evaluate the latest response, replying with whether the response is acceptable and your feedback."
        return evaluator_system_prompt 

    def evaluator_user_prompt(self, reply, message, history):
        user_prompt = f"Here's the conversation between the User and the Agent: \n\n{history}\n\n"
        user_prompt += f"Here's the latest message from the User: \n\n{message}\n\n"
        user_prompt += f"Here's the latest response from the Agent: \n\n{reply}\n\n"
        user_prompt += "Please evaluate the response, replying with whether it is acceptable and your feedback."
        return user_prompt

    def evaluate(self, reply, message, history) -> Evaluation:

        messages = [{"role": "system", "content": self.evaluator_system_prompt()}] + [{"role": "user", "content": self.evaluator_user_prompt(reply, message, history)}]
        response = with_retry(lambda: self.openai.beta.chat.completions.parse(model=EVALUATOR_MODEL, messages=messages, response_format=Evaluation))
        return response.choices[0].message.parsed

    def rerun(self, reply, message, history, feedback):
        updated_system_prompt = self.system_prompt + "\n\n## Previous answer rejected\nYou just tried to reply, but the quality control rejected your reply\n"
        updated_system_prompt += f"## Your attempted answer:\n{reply}\n\n"
        updated_system_prompt += f"## Reason for rejection:\n{feedback}\n\n"
        messages = [{"role": "system", "content": updated_system_prompt}] + history + [{"role": "user", "content": message}]
        response = with_retry(lambda: self.openai.chat.completions.create(model=MODEL, messages=messages))
        return response.choices[0].message.content
   
    
    def chat(self, message, history):
        try:
            return self._chat(message, history)
        except Exception as e:
            print(f"Chat failed: {type(e).__name__} {e}", flush=True)
            return ("Sorry, I'm having a moment on my end. Please try that again in a few seconds, "
                    "or reach me directly at akivakaufman@gmail.com.")

    def _chat(self, message, history):
        user_message = message
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = with_retry(lambda: self.openai.chat.completions.create(model=MODEL, messages=messages, tools=tools))
            if response.choices[0].finish_reason=="tool_calls":
                assistant_message = response.choices[0].message
                results = self.handle_tool_call(assistant_message.tool_calls)
                messages.append(assistant_message)
                messages.extend(results)
            else:
                done = True
        reply = response.choices[0].message.content
        evaluation = self.evaluate(reply, user_message, history)
        if evaluation.is_acceptable:
            print("Passed evaluation - returning reply")
        else:
            print("Failed evaluation - retrying")
            print(evaluation.feedback)
            reply = self.rerun(reply, user_message, history, evaluation.feedback)
        return reply




CSS = """
.gradio-container { max-width: 100% !important; padding: 0 !important; box-sizing: border-box !important; }
footer { display: none !important; }

/* title: responsive sizes to match the site */
.gradio-container h1 { font-size: 1.25rem !important; font-weight: 700 !important; margin: 0.5rem 0 0.25rem !important; }
@media (min-width: 768px) {
  .gradio-container h1 { font-size: 1.5rem !important; }
}

/* chat panel + input box: square black borders to match the site */
#chatbot { border: 2px solid #111827 !important; border-radius: 0 !important; }
#chat-input { border: 2px solid #111827 !important; border-radius: 0 !important; }
#chat-input textarea { border: none !important; box-shadow: none !important; }
"""

if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(
        me.chat,
        type="messages",
        chatbot=gr.Chatbot(elem_id="chatbot", type="messages", height=400, label="Chat"),
        textbox=gr.Textbox(elem_id="chat-input", placeholder="Ask me a question..."),
        title="Ask me anything",
        css=CSS,
    ).launch()
    
