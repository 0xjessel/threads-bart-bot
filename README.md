# @sfbartalerts

<img src="https://raw.githubusercontent.com/0xjessel/threads-bart-bot/main/images/profile_pic.png" alt="Profile Pic" width="300px">

Follow my [Threads profile](https://www.threads.net/@sfbartalerts)!

# Why

We recently launched the Threads API and my goal with this project is to 1) understand how it works and 2) inspire other developers to build more bots for Threads.  

I also take BART regularly into the office and would benefit from getting realtime updates if there are any important advisories during my commute.

I also used this opportunity to try out Cursor, the new AI code editor, to see how quickly AI can put together a simple bot.  Verdict: it's pretty damn good.  Except it struggles hard with parsing dates and timezones, just like humans.

# Overview

`fetch_and_post_bart_advisories.py` is run via a cron job on Dreamhost that is scheduled to run every 5 minutes.

`fetch_advisories()` gets the latest data from the BART API, although their API is quite flaky so retries are necessary.  It parses the time and advisory strings, and will only return relevant advisories that were posted within 5 minutes of the current time.  

`post_to_threads()` takes the advisory strings and calls the threads API to publish a post.  

I also schedule `refresh_access_token.py` to be a cron job that's run every month to keep the access token valid.  

# Random thoughts

Why is BART API so flaky.  Why does BART use 24h time formatting but then also includes AM/PM.  WHY?!

Writing test cases via AI is awesome.  
