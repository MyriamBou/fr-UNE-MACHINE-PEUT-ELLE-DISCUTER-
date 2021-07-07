import discord
from discord.ext import commands
import datetime
import os
from nltk.chat.util import Chat, reflections
from sklearn.linear_model import SGDClassifier
from pairs import pairs
from dotenv import load_dotenv
from pymongo import MongoClient
import pickle
import random
import re
import asyncio
from sklearn.preprocessing import LabelEncoder
import time

import numpy as np

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer


connection = MongoClient("mongodb+srv://Ludor:PWD.rtjfn.mongodb.net/StarkBotBD?retryWrites=true&w=majority")
db = connection["StarkBotBD"]
collection = "Quest_Rep"

load_dotenv(dotenv_path="config")

bot = commands.Bot(command_prefix = "!", description = "Bot numéro 1")
date = datetime.datetime.now()

emotion = pickle.load(open("./models/emotion.sav", 'rb'))

## model classifier Topic
filename = "./models/classifier_topic.pickle"
classif_topic = pickle.load(open(filename, 'rb'))
topics = ['astronomy', 'earthscience', 'electronics', 'engineering', 'space', 'stellar', 'general']
#topics = db.Quest_Rep.distinct('Topic')
nb_topics = len(topics)

le_topic = LabelEncoder()
le_topic.fit(topics)

## model classifier language
filename = "./models/classifier_language.pickle"
classif_language = pickle.load(open(filename, 'rb'))
languages = ['english', 'french']
le_language = LabelEncoder()
le_language.fit(languages)

class Stark(discord.Client, Chat):

    ## Init : Stark class inherits from discord.Cliend and nltk.Chat
    def __init__(self, pairs, reflections, flag=True):
        discord.Client.__init__(self)
        Chat.__init__(self, pairs, reflections)
        self.flag = flag
        self.flag = True
        self.threshold_en = 0.6
        self.threshold_fr = 0.2
        self.chatterbot_french = self.chatterbot_fcn('jarvis','french' )
        self.chatterbot_english = self.chatterbot_fcn('jarvis','english' )

    ## nltk chat bot    
    def nltk_respond(self, message):
        return self.respond(message)

    ## Chatterbot
    def chatterbot_fcn(self, nom, language):
        
        chatbot = ChatBot(nom, logic_adapters=[
                                'chatterbot.logic.MathematicalEvaluation',
                                'chatterbot.logic.BestMatch'
                            ],
                        )
        trainer = ChatterBotCorpusTrainer(chatbot)
        # Corpus d'entrainement
        if language=='english':
            trainer.train(
                "chatterbot.corpus.english"
            )
        elif language=='french':
            trainer.train(
                'chatterbot.corpus.french'
            )
        return chatbot

    
    ## Query Database
    def mongodb_respond(self, mess, topic):
        
        title = db.Quest_Rep.find({"$text": {"$search": mess}, 'Topic':topic, 'AnswerCount': {"$ne": "0"}}, {'score': {'$meta': 'textScore'}})
        title.sort([('score', {'$meta': 'textScore'})]).limit(1)

        ParentId = title[0].get("Id")
        if isinstance(ParentId, int):
            ParentId = str(ParentId)

        all_resp = db.Quest_Rep.find({'Topic':topic, "ParentId":ParentId}).sort([('Score', -1)]).limit(5)
        list_resp = [resp.get("Body") for resp in all_resp]
        
        final_resp = []
        for i in list_resp:
            i = re.sub('<[^<]+?>', '', i)
            final_resp.append(i)

        return final_resp, ParentId

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await client.get_channel(808617144504811584).send("```   __,_,\n  [_|_/           Hello there i'm Online\n   //\n _//    __            J.A.R.V.I.S\n(_|)   |@@|\n \ \__ \--/ __            Stark Agency\n  \o__|----|  |   __\n      \ }{ /\ )_ / _\ \n      /\__/\ \__O (__\n     (--/\--)    \__/\n     _)(  )(_                                        ID: CAABMBJMOPLR\n    `---''---`\n```")
        
        ## Auto message on start every 5 minutes
        timeout = 60*60  # 5 minutes
        messauto = "```Hey Human !\n\nI would be pleased to help you on any topic in astronomy, earthscience, electronic, engineering and Space fields !\n\nPlease feel free to adress me your concern any time.\nFor more information you may just type : \help\n\nActually, my masters are working on an amazing BOT Challenge brief !\nIf you are curious, you may download the brief here :\n\nhttps://cdn.discordapp.com/attachments/783660084395769887/808333411948429322/Brief-IA-Methodes-Agiles_-_Sprint_1.pdf\n\nHave a nice day !```"
        while True:
            await client.get_channel(808617144504811584).send(messauto)
            await asyncio.sleep(timeout)

    
    async def on_message(self, message):
        mess = message.content
        mess = mess.lower() 

        ## Do not respond itself 
        if message.author == self.user:
            return
        else:
            ## Base commands of the bot
            if mess.startswith("\\"):
                if mess == "\\unmute":
                    self.flag = True
                    await message.channel.send("Hey there, nice to see you ! How may I help you ?")

                if mess == "\\mute":
                    self.flag = False
                    await message.channel.send("Thanks, I was pleased to see you !")
                    msg = await message.channel.send("```Would you please rate your user experience journey ?```")
                    await msg.add_reaction('😃')
                    await msg.add_reaction('😐')
                    await msg.add_reaction('🙁')
                        
                    reac_list = ['😃','😐','🙁']
                    check = lambda reaction, user: user == message.author and str(reaction) in reac_list

                    try:    
                    # Waiting for the reaction
                        reaction, user = await client.wait_for('reaction_add', check=check, timeout=10.0)
                        if str(reaction) == "😃":
                            db.Rating.insert_one({"rate":2 })
                            await message.channel.send("```Thank you, I was pleased to help you !```")

                        if str(reaction) == "😐":
                            db.Rating.insert_one({"rate":1 })
                            await message.channel.send("```Thank you, I hope I will do better next time !```")

                        if str(reaction) == "🙁":
                            db.Rating.insert_one({"rate":0 })
                            await message.channel.send("```Thank you, I hope I will do better next time !```") 

                    except asyncio.TimeoutError:
                        await msg.delete()

                if mess == "\\shutdown":
                        await message.channel.send("Bye bye !")
                        await self.logout()

                if self.flag == True:
                    if mess.startswith("\\suggestion"):
                        request = mess[12:]
                        db.Suggestion.insert_one({"User":str(message.author), "Suggestion":request})
                        await message.channel.send("Thank you **%s** for the suggestion  : **%s**" %(str(message.author)[:-5], request))
                    if mess.startswith("\\imp"):
                        listmess = mess.split(sep=" ")
                        PID = listmess[1]
                        TOP = listmess[2]
                        BODlist = listmess[3:]
                        BOD = "[NON VERIFIED] %s" %' '.join(BODlist)
                        db.Quest_Rep.insert_one({"Topic":TOP,"Body":BOD,"ParentId":PID, "PostTypeId":2, "Score":10})
                        await message.channel.send("Thank you for this valuable contribution!")
                    if mess == "\\get rating":
                        list_rating = db.Rating.find()
                        bot_ratings = [resp.get("rate") for resp in list_rating]
                        good = bot_ratings.count(2)
                        medium = bot_ratings.count(1)
                        bad = bot_ratings.count(0)
                        await message.channel.send("Bot rating  :\n\nGood -> **%s**\nMedium -> **%s**\nBad -> **%s**" % (good, medium, bad))
                    if mess == "\\get suggestion":
                        list_sugg = db.Suggestion.find()
                        bot_sugg = [resp.get("Suggestion") for resp in list_sugg]
                        print(bot_sugg)
                        bot_sugg = '    ;   '.join(bot_sugg)
                        with open("result.txt", "w") as file:
                            file.write(bot_sugg)
                        with open("result.txt", "rb") as file:
                            await message.channel.send("Your file is:", file=discord.File(file, "result.txt"))
                        os.remove("result.txt")
                    if mess == "\\emotion":
                        list_emotion = db.Emotion.find({"User":str(message.author)})
                        list_feel = [resp.get("Message") for resp in list_emotion]
                        list_feel = ' '.join(list_feel)
                        list_feel = [list_feel]
                        feel = emotion.predict(list_feel)
                        await message.channel.send("Hey! Looks like you feel: %s" %feel)                        
                    if mess == "\\help":
                        await message.channel.send("```css\nHey %s ! I'm .J.A.R.V.I.S. !\n\nI am the super cool robot created by the renowned :STARK-Agency !\nMy masters are teaching me to imitate you to steal your life !\nIn the meantime, I’m gonna explain how I work to make you believe that I am here to help you \n\nAt the moment I am an expert in astronomy, earthscience, electronic, engineering and Space. You may adrress me anything on this topics !\n\nYou can use the commands bellow :\n\n   - \\unmute -> To (re)activate \n\n   - \mute -> If i am too chatty and you even may kindly rate our interaction \n\n   - \suggestion  -> To make a suggestion\n\n   - \ping -> Just for fun, I will be playefull by responding Pong.. \n\n   - \date -> To get the daily date ! \n\n   - \\bonjour -> For a smile !\n\n   - \emotion -> To predict your daily mood \n\n   - \imp -> 'Id' 'Topic' your message \n\nYou may also check the documentation on :http://jarvis.github.com```" % str(message.author)[:-5])
                    if mess == "\\ping":
                        await message.channel.send("Pong ! joke.. Your ping : {:.0f} ms".format(self.latency * 1000))
                    if mess == "\\date":
                        await message.channel.send("**%s**" % str(date)[:-7])
                    if mess == "\\test":
                        await message.channel.send("```  __,_,\n  [_|_/           Hello there I'm here at your service !\n   //\n _//    __            J.A.R.V.I.S\n(_|)   |@@|\n \ \__ \--/ __            Stark Agency\n  \o__|----|  |   __\n      \ }{ /\ )_ / _\ \n      /\__/\ \__O (__\n     (--/\--)    \__/\n     _)(  )(_                                        ID: CAABMBJMOPLR\n    `---''---`\n```")
                    if mess == "\\bonjour":
                        await message.channel.send("Bonjour **%s** :smiley:" % str(message.author)[:-5])


                ## Discution
            else:
                if self.flag == True:
                    ## Topic identification
                    topic = classif_topic.predict([mess])
                    topic = le_topic.inverse_transform(topic)
                    liste_posible_values = list(range(nb_topics))
                    liste_topic = list(le_topic.inverse_transform(liste_posible_values))
                    pred_proba = classif_topic.predict_proba([mess])
                    liste_proba = list(pred_proba[0])

                    ## Language identification
                    language = classif_language.predict([mess])
                    language = le_language.inverse_transform(language)
                    print(language[0])

                    ## nltk chat part 
                    flag_resp = False
                    resp = self.nltk_respond(mess)
                    if resp :
                        flag_resp = True
                        db.Emotion.insert_one({"User":str(message.author), "Message":mess, "Date":str(date)[:-7]})
                        await message.channel.send(resp)

                    ## Chatterbot
                    if (topic[0]=='general') and (flag_resp==False):
                        mess_chatterbot = mess.upper()
                        db.Emotion.insert_one({"User":str(message.author), "Message":mess, "Date":str(date)[:-7]})
                        if language[0]=='english':
                            resp = self.chatterbot_english.get_response(mess_chatterbot)
                            print('mess :', mess_chatterbot, 'chatterbot english, resp :', resp, ', confidence', resp.confidence)
                            if resp.confidence>=self.threshold_en:
                                flag_resp = True
                                await message.channel.send(resp)
                        elif language[0]=='french':
                            resp = self.chatterbot_french.get_response(mess_chatterbot)
                            print('mess :', mess_chatterbot, 'chatterbot french, resp :', resp, ', confidence', resp.confidence)
                            if resp.confidence>=self.threshold_fr:
                                flag_resp = True
                                await message.channel.send(resp)
                        ##else:

                    ## Query mongodb DataBase
                    
                    if flag_resp==False:
                        if topic[0]!='general':
                            for i in range(nb_topics):
                                best_topic = liste_topic[np.argmax(liste_proba)]
                                msg = await message.channel.send("Are you looking for information about %s ?\nWould you please confirm by yes or no" %best_topic)
                                await msg.add_reaction('✅')
                                await msg.add_reaction('❌')
                                    
                                reac_list = ['✅','❌']
                                check = lambda reaction, user: user == message.author and str(reaction) in reac_list
                                try:
                                # Waiting for the reaction
                                    reaction, user = await client.wait_for('reaction_add', check=check, timeout=30.0)
                                    if str(reaction) == "✅":
                                        print("ok")
                                        break
                                    if str(reaction) == "❌":
                                        print("switch")
                                        idx = np.argmax(liste_proba)
                                        liste_proba.pop(idx)
                                        liste_topic.pop(idx)

                                except asyncio.TimeoutError:
                                    print("async")
                        else: best_topic = topic[0]
                        try:
                            pic = await message.channel.send(file=discord.File('./assets/wait.gif'))

                            resp, quest_id = self.mongodb_respond(mess, best_topic)
                            await pic.delete()

                            for i in resp:
                                if len(i) > 1900:
                                    i1 = i[:1900]
                                    i2 = i[1901:]
                                    await message.channel.send(i1)
                                    await message.channel.send(i2)

                                else:
                                    await message.channel.send(i)
                                msg = await message.channel.send("```Would you kindly help us to improve our bot by rating the relevance of the answer```")
                                await msg.add_reaction('👍')
                                await msg.add_reaction('👎')
                            
                                reac_list = ['👍','👎']
                                check = lambda reaction, user: user == message.author and str(reaction) in reac_list
                                try:
                                # Waiting for the reaction
                                    reaction, user = await client.wait_for('reaction_add', check=check, timeout=60.0)

                                    if str(reaction) == "👍":
                                        await message.channel.send("```Thank you for your amazing feedback ! If I was human I would be the happiest !```")
                                        break
                                    if str(reaction) == "👎":
                                        await message.channel.send("```Thank you for your feedback !\nWould you help us to become better by adding an anwser by typing : \\imp %s %s ANSWER```"%(quest_id, best_topic))
                                except asyncio.TimeoutError:
                                    await msg.delete()
                                    break  
                        except IndexError:
                            await pic.delete()
                            resp = "I'm just a 3 days old baby, I'm still learning.\n Would you help me by telling me what do you mean by **%s** ?"%mess
                            await message.channel.send("%s"%resp)

with open('token.tok') as f:
    tok = f.read()
TOKEN = tok

client = Stark(pairs, reflections)
#client.run(os.getenv("TOKEN"))  
client.run(TOKEN)
