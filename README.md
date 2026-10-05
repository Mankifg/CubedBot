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

## Optional database logs

Terminal logs can be retained in Supabase for seven days. Run
`sql/001_bot_logs.sql` manually in the intended Supabase project, then set
`DATABASE_LOGGING_ENABLED=1` for that bot instance. Logging remains disabled
when the variable is absent, so code can be deployed before the database setup.
The logger requires the bot's server-side secret/service-role key; public roles
have no access to the log table.
