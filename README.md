# roblox elo-bot

Setup for discord and google sheets API can be found in the old repository. [old](https://github.com/mikewakeham/roblox-elo-bot-light/tree/main)

```
creds = ServiceAccountCredentials.from_json_keyfile_name("GOOGLE API CREDENTIALS JSON FILE HERE", scope)

return client.open("DATABASE NAME").sheet1 
```
are both in the sheets file

```
bot.run("DISCORD API TOKEN HERE")
```
is still at the bottom of the bot file

# Installation

Clone repository:

```
git clone https://github.com/mikewakeham/elo-bot
```

Navigate to directory:

```
cd elo-bot
```

Install dependencies:

```
pip install -r requirements.txt
```

