![Thumbnail](/assets/images/thumbnail.png)
# Cubed bot
Discord bot for Rubik's cube competitions. It it also capable of displaying WCA profiles.

# Info
Bot is currents private but you can local host it, [instructions](/README.md/#instructions) bellow.




## Download & Run

### Requirements
You will need:
* [Python](https://www.python.org/downloads/) (3.10+ works)
* Discord bot account 
* Supabase project




# Thanks
This bot uses following features:
* [supabase](https://supabase.com/) - storing data in database
* [pyTwistyScrambler](https://github.com/euphwes/pyTwistyScrambler) - generating random scrambles

## Database logs

Terminal logs can be retained in Supabase for seven days. Run
`sql/001_bot_logs.sql` manually in the intended Supabase project. Logging is
enabled by default; set `DATABASE_LOGGING_ENABLED=0` only when it needs to be
disabled explicitly. The logger requires the bot's server-side
secret/service-role key; public roles have no access to the log table.
