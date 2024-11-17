# @sfbartalerts

<img src="https://raw.githubusercontent.com/0xjessel/threads-bart-bot/main/images/profile_pic.png" alt="Profile Pic" width="300px">

Follow my [Threads profile](https://www.threads.net/@sfbartalerts)!

# Why

We recently launched the Threads API and my goal with this project is to 1) understand how it works and 2) inspire developers to build more useful bots for Threads.  

I also take BART regularly into the office and would benefit from getting realtime updates if there are any important advisories during my commute.

I also used this opportunity to try out Cursor, the new AI code editor, to see how quickly AI can put together a simple bot.  Verdict: it's pretty damn good.  Except it struggles hard with parsing dates and timezones, just like humans.

# Overview

`fetch_and_post_bart_advisories.py` is run via a cron job on Dreamhost that is scheduled to run every 5 minutes.

`fetch_advisories()` gets the latest data from the BART API, although their API is quite flaky so retries are necessary.  It parses the time and advisory strings, and will only return relevant advisories that were posted within 5 minutes of the current time.  

`post_to_threads()` takes the advisory strings and calls the threads API to publish a post.  

I also schedule `refresh_access_token.py` to be a cron job that's run every month to keep the access token valid.  

# Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/0xjessel/threads-bart-bot.git
   cd threads-bart-bot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create a `.env.local` file:**
   - Copy the `.env.example` file to create your own environment configuration:
     ```bash
     cp .env.example .env.local
     ```
6. **Set up your env file**
   - [Get your BART API key](https://api.bart.gov/api/register.aspx)
   - [Get your Threads API key and secret by creating a Meta app created with the Threads use case](https://developers.facebook.com/docs/development/create-an-app/threads-use-case)
   - [Get your Threads account's User ID](https://developers.facebook.com/docs/threads/threads-profiles/)
       - Don't forget to add your Threads account as a "Threads Tester" under App Roles > Roles and approve the request
   - [Get your Threads access token](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions)

6. **Edit the `.env.local` file:**
   - Open `.env.local` in a text editor and fill in the required values

7. **Run the script**
```bash
python fetch_and_post_bart_advisories.py
```

8. **Run tests**
```bash
python -m unittest test_fetch_advisories.py
```

# Random thoughts

Why is BART API so flaky.  Why does BART use 24h time formatting but then also includes AM/PM.  WHY?!

Writing test cases via AI is awesome.  
