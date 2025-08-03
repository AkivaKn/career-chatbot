# Career Chatbot

Career Chatbot is an interactive resume application designed to represent Akiva Kaufman professionally. It uses OpenAI and Gradio to provide a conversational interface for potential clients or employers.

This project was created with the help of the Udemy course by Ed Donner: [The Complete Agentic AI Engineering Course](https://beartech.udemy.com/course/the-complete-agentic-ai-engineering-course/).

## Features

- Chat interface powered by Gradio.
- Email notifications for user details and unanswered questions.
- Integration with OpenAI and Google Gemini APIs.
- Processes resume and LinkedIn data for personalised responses.

## Setup Instructions

### Prerequisites

1. **Install `uv`**  
   Follow the instructions here: [UV Installation Guide](https://docs.astral.sh/uv/getting-started/installation/).  
   It is recommended to use the **Standalone Installer** approach mentioned at the top of the guide.

2. **Clone this repository and navigate to the project directory**  

   ```sh
   git clone <repository-url>
   cd career-chatbot
   ```

3. **Add Environment Variables**  
   Copy the `.env.example` file to `.env`:

   ```sh
   cp .env.example .env
   ```

   Fill in the `.env` file with your credentials and API keys.

4. **Install Dependencies**  
   Run the following command to sync and install all dependencies:

   ```sh
   uv sync
   ```

---

### Run Locally

To start the application locally, use:

```sh
uv run app.py
```

---

### Deploy to Gradio

To deploy the application to Gradio, use:

```sh
cd app/
uv run dotenv -f .env run gradio deploy
```

---

### Author

This project was created by **Akiva Kaufman**.  
For any questions or additional information, feel free to reach out at:  
**Email**: akivakaufman@gmail.com

---

### Acknowledgements

Special thanks to **Ed Donner** for his Udemy course, [The Complete Agentic AI Engineering Course](https://beartech.udemy.com/course/the-complete-agentic-ai-engineering-course/), which provided valuable guidance in creating this project.