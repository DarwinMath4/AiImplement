import os
from flask import Flask, jsonify, redirect, render_template, request, url_for
import requests
from bs4 import BeautifulSoup
from OPENAI_API_KEY import api_data
import openai
import time



app = Flask(__name__, template_folder='templates')

# Ensure you have your OpenAI API key set in your environment variables or configure it directly
openai.api_key = api_data

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/info')
def infoPage():
    return render_template('info.html')

def search():
    user_query = request.form.get('sentence')
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    try:
        # Assuming you have set up OpenAI API key correctly
        response = openai.completions.create(
          engine="text-davinci-003",
          prompt=user_query,
          temperature=0.5,
          max_tokens=2048,
          top_p=1.0,
          frequency_penalty=0.0,
          presence_penalty=0.0
        )
        answer = response.choices[0].text.strip()
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_google_dork_urls(base_query):
    base_url = "https://www.google.com/search?q="
    dork_patterns = [
        f'"{base_query}"',
        f'{base_query} site:facebook.com OR site:instagram.com OR site:twitter.com OR site:myspace.com OR site:snapchat.com OR site:x.com OR site:tiktok.com OR site:pinterest.com',
        f'{base_query} filetype:pdf OR filetype:doc OR filetype:docx',
        f'{base_query} "contact" OR "about" site:.org OR site:.com',
        f'{base_query} email OR contact OR @ OR address OR phone number',
    ]
    return [base_url + requests.utils.quote(dork_query) for dork_query in dork_patterns]


def save_webpage_text(url, output_file_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        with open(output_file_path, 'a', encoding='utf-8') as file:
            file.write(f"\n\nURL: {url}\n{text}")
        print(f"Webpage text for {url} has been saved.")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")


def setup_openai():
    # Initialize the OpenAI client
    client = openai.OpenAI()


    # Create a file in OpenAI
    file = client.files.create(
        file=open('dump_text.txt', "rb"),
        purpose='assistants'
    )


    # Create an Assistant
    assistant = client.beta.assistants.create(
        name="EnumSpider",
        instructions="Read the provided .txt file and provide useful data for OSINT analysis.",
        model="gpt-4-1106-preview",
        tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
        file_ids=[file.id]
    )


    # Create a Thread
    thread = client.beta.threads.create()


    return client, assistant.id, thread.id

@app.route('/query_openai', methods=['POST'])
def query_openai(client, assistant_id, thread_id, query):
    # Add a Message to a Thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="Please review the provided documentation and provide a detailed list based on: " + query
    )


    # Run the Assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="Task: Provide the user with useful data for OSINT analysis."
    )


    check_run_status(client, thread_id, run.id)


def check_run_status(client, thread_id, run_id):
    while True:
        time.sleep(5)  # Delay for API rate limiting
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run_status.status == 'completed':
            display_messages(client, thread_id)
            break
        else:
            print("Processing...")


def display_messages(client, thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in messages.data:
        print(f"{msg.role.capitalize()}: {msg.content[0].text.value}")


@app.route('/submit', methods=['POST'])
def submit():
    # Aggregate form inputs into a single query string
    name = request.form.get('name')
    email = request.form.get('email')
    school = request.form.get('school')
    employment = request.form.get('employment')
    phone = request.form.get('phone')
    # Concatenate other form inputs as needed
    base_query = f"{name} {email} {school} {employment} {phone}"  # Modify this line as per your form fields

    # Placeholder for where you'd process the base_query
    # For demonstration, just print the base_query to the console
    print(f"Base Query: {base_query}")
    google_dork_urls = generate_google_dork_urls(base_query)
    output_path = r'C:\Users\cutle\Forward_Op\Notebook\dump_text.txt'
    for url in google_dork_urls:
        print(f"Processing: {url}")
        save_webpage_text(url, output_path)
    # Normally, here you'd call your functions to process the base_query
        open(output_path, 'w').close()

    return redirect(url_for('infoPage'))

    

def main():
    #base_query = input("Please enter your query: ")
    #google_dork_urls = generate_google_dork_urls(base_query)
    
    #Output
    #output_path = 'dump_text.txt'
   
    # Clear previous content before appending new webpage text
    #open(output_path, 'w').close()  # This clears the file before the new run
   
    #for url in google_dork_urls:
     #   save_webpage_text(url, output_path)
    submit()

    '''
    client, assistant_id, thread_id = setup_openai()


    while True:
        user_query = input("What do you want to know? (Type 'exit' to quit): ")
        if user_query.lower() == 'exit':
            break
        query_openai(client, assistant_id, thread_id, user_query)
        '''


if __name__ == "__main__":
    app.run(debug=True)
