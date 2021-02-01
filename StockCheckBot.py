import os
import discord
import asyncio
import time
import datetime
from dotenv import load_dotenv
from discord.ext import commands, tasks
import requests 
import sys
import re
import yagmail
import math
from bs4 import BeautifulSoup

#get discord token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

#declare intents
intents = discord.Intents.default()
intents.messages = True
intents.members = True

#initialize bot with command prefix !
bot = commands.Bot(command_prefix = '%', intents = intents)
#removes the default help command so we can replace it with custom help command
bot.remove_command('help')
#set the bot's commands to be case-insensitive
bot.case_insensitive = True

user_list = []

#open the list of notification users or create it if it doesn't exist
try: 
	with open('notifyFile.txt', 'r+') as userFile:
		user_data = userFile.readlines()
		for line in user_data:
			user_name = line.split(',')[0]
			user_id = line.split(',')[1]
			user_list.append([user_name, user_id])
	userFile.close()
except OSError as e:
		print(f'File does not exist. Creating File...')
		userFile = open("notifyFile.txt", "x")
		userFile.close()

#-------------------------- EVENTS-------------------------------

#on_ready event
@bot.event
async def on_ready():
	print(f'{bot.user} is ready')
	#await bot.wait_until_ready()
	#channel = bot.get_channel(804688518638075955)
	#await channel.send('Stock Checker is connected!')

#change status every 10 seconds
async def status_task():
	await bot.wait_until_ready()
	while True:
		try:
			await bot.change_presence(activity = discord.Game('Checking Stock'), status = discord.Status.online)
			await asyncio.sleep(10)
			await bot.change_presence(activity = discord.Game('use !help for a list of commands'), status = discord.Status.online)
			await asyncio.sleep(10)
		except Exception as e:
			print('An Error occured while changing statuses. Oh well.')

async def stock_task():
	await bot.wait_until_ready()
	#set channel variable to stock-checker channel
	channel = bot.get_channel(804688518638075955)
	#attempt to grab existing embeds for editing
	embed_message1 = channel.get_partial_message(804970589411606558)
	embed_message2 = channel.get_partial_message(804970590389141534)

	while(True):
		stock_embed = discord.Embed()
		stock_embed.title = f'Stock Levels as of {datetime.datetime.now().strftime("%I:%M:%S:%p")}'
		stock_embed.set_footer(text = "Good Luck!")

		holding_embed = discord.Embed()

		#Reinitilizing the list every time it is run is kinda sucky for processing time but this
		#should hoefully allow me to update the item list in real time without having to stop the bot.
		URL_list = []

		#open the items list and add them to URL_list to be processed
		with open('items.txt', 'r') as URLfile:
			item_data = URLfile.readlines()

		#list of items to check stock for
		#Format 
		#[0] CanCom or MemEx depending on store
		#[1] URL of item
		#[2] Name of item to print

		for line in item_data:
			site = line.split(",")[0]
			site_url = line.split(",")[1]
			site_item = line.split(",")[2]
			site_category = line.split(",")[3]
			URL_list.append([site, site_url, site_item])

		URLfile.close()

		for url in URL_list:
			#print(f'Processing {url[0]} : {url[2]}')
			#initialization of BeautifulSoup object
			with requests.Session() as s:
				stock_value = str('')
				stock_name = str(f'{url[0]} : {url[2]} : ')
				try:
					page = s.get(url[1])
					soup = BeautifulSoup(page.content, 'html.parser')
					#reset stock to 0 for every item
					total_stock = 0
					
					receivers = ["ttsang96@gmail.com"]
					
					#Memory Express 
					if url[0] == 'MemEx':
						MemExAvail_elem = soup.find_all('div', class_='c-capr-inventory-store')
						#Define list of stores to check
						store_list = ['Vancouver','Burnaby','Langley']	
						
						for store in MemExAvail_elem:
							storeName = store.find(class_='c-capr-inventory-store__name')
							#if the store name is in list of stores, grab stock level
							if any(ele in storeName.text for ele in store_list):
								storeAvail = store.find(class_='c-capr-inventory-store__availability')
								StoreStock = storeAvail.text.replace('\n','').replace('\r','').replace(' ', '')
								StoreStock = re.sub("[^0-9]", "", StoreStock)
								#add stock level to total stock level
								if StoreStock.isdigit():
									total_stock += int(StoreStock)					
					#Canada Computers
					elif url[0] == 'CanCom':
						CanComAvail_elem = soup.find('div', class_='stocklevel-pop')
						CanComAvail_prov = CanComAvail_elem.find_all('div', class_='row col-border-bottom pt-1')
						#Define list of provinces to check (fucking Ontarioooooo)
						prov_list = ['Online Store', 'British Columbia']
						#Define list of stores to check (god damn Richmond Hill in Ontario)
						store_list = ['Burnaby', 'Port Coquitlam', 'East Vancouver', 'Richmond', 'Vancouver Broadway', 'Online Store', 'BC Special Order Warehouse']
						
						for prov in CanComAvail_prov:
							CanComProv = prov.find('p').text
							#if the province name is in list of provinces
							if any(ele in CanComProv for ele in prov_list):
								Stores = prov.find_all('div', 'col-md-4 col-sm-6')
								
								for Store in Stores:
									StoreName = Store.find('p').text
									#if the store name is in the list of stores, grab stock level
									if any(ele1 in StoreName for ele1 in store_list):
										Stock = Store.find('div', class_='item-stock').text.replace('\n','').replace('\r','').replace(' ', '')
										Stock = re.sub("[^0-9]", "", Stock)
										#add stock level to total stock level
										if Stock.isdigit():
											total_stock += int(Stock)
					elif url[0] == 'Newegg':
						NeweggAvail_elem = soup.find('div', class_='product-wrap')
						NeweggAvail_prod = NeweggAvail_elem.find('div', class_='product-offer')
						NeweggAvail_InStock = NeweggAvail_elem.find('div', class_='product-inventory')
						
						if NeweggAvail_prod is not None:
							Newegg_text = NeweggAvail_prod.find('span')
							if 'New' in Newegg_text:
								stock = re.sub("[^0-9]", "", Newegg_text)
								total_stock += int(stock)
						elif NeweggAvail_InStock is not None:
							Newegg_text = NeweggAvail_InStock.find('strong').text
							if 'In stock' in Newegg_text:
								total_stock += 1
						
					if total_stock > 0:
						stock_value += str(f"```css\nIn Stock, {str(total_stock)} items @ {url[1]}```")
						
						if '3080' in url[2]: 
							for email in receivers:
								yag = yagmail.SMTP("ttsang96@gmail.com", 'Superbad1#')
								yag.send(
									to='tristant96@live.ca',
									subject="3080 in Stock @ " + url[1] + "!",
									contents=url[1]
								)
							for user in user_list:
								bot.get_user(user[1]).send(f'3080 in Stock @ {url[1]}!')

					else:
						stock_value += str('```prolog\nOut Of Stock```')
					#print(f'Adding {stock_name} {stock_value} to stock_embed')
					holding_embed.add_field(name = f'{stock_name}', value = stock_value)
				except Exception as e:
					stock_value += ' Connection Error'
		
		"""
		for field in holding_embed.fields:
			print(f'{field.name} {field.value}')
		
		#max length of an embed field is 6000 characters
		print(f'holding_embed length: {len(holding_embed)}')
		
		
		print(f'holding_embed fields: {len(holding_embed.fields)}')
		"""
		#max number of fields in one embed is 25, split embed into parts
		if (len(holding_embed.fields) > 25):
			#print('holding_embed has over 25 fields. Splitting holding_embed.')

			stock_embed2 = discord.Embed()
			stock_embed2.title = f'Stock Levels as of {datetime.datetime.now().strftime("%I:%M:%S:%p")} - Page 2'
			stock_embed2.set_footer(text = "Good Luck!") 

			for fields in holding_embed.fields[0:24]:
				stock_embed.add_field(name = fields.name, value = fields.value)
			for fields in holding_embed.fields[25:49]:
				stock_embed2.add_field(name = fields.name, value = fields.value)		

			if (embed_message1 is not None):
				await embed_message1.edit(embed = stock_embed)
			else:	
				await channel.send(embed = stock_embed)

			if (embed_message1 is not None):	
				await embed_message2.edit(embed = stock_embed2)
			else:
				await channel.send(embed = stock_embed2)
		else:
			if (embed_message1 is not None):
				await embed_message1.edit(embed = stock_embed)
			else:	
				await channel.send(embed = stock_embed)	
		await asyncio.sleep(60)
#--------------------------COMMANDS------------------------------

#responds in channel with the author's ID 
@bot.command(name = 'id', help = f"DM's the user their user ID")
async def id(ctx):
	await ctx.author.send(ctx.author.id)
	await ctx.message.delete

#dms the user their name + number
@bot.command(name = 'dm', help = "DM's the user their username + user number")
async def dm(ctx):
	await bot.wait_until_ready()
	userID = 71766375550431232
	await ctx.author.send(f'Username: {await bot.fetch_user(userID)}')
	await ctx.message.delete

#disconnect command
@bot.command(name = 'logout', help = 'Disconnect command. Calling restricted.')
async def logout(ctx):
	if (ctx.author.id == 71766375550431232):
		await ctx.message.delete
		await ctx.bot.close()
		time.sleep(1)
		
#notify command
@bot.command(name = 'notify', help = 'Adds user to notification list for the specified item')
async def notify(ctx, item_category):
	#only allow users to add themselves to a notification list for items that are currently being tracked.
	#this list must be updated every time a new item category is added to items.txt
	if (item_category not in ('3080', '5900X')):
		delete_message = await ctx.send(f"User <@{ctx.author.id}> the item {item_category} doesn't exist.")
		await ctx.message.delete(delay = 10.0)
		await delete_message.delete(delay = 10.0)
	else:
		with open('notifyFile.txt', 'r+') as notifyFile:
			notify_data = notifyFile.read()
			#adds the user to the notification list if the user isn't already on the list
			if (f'{ctx.author.name}, {ctx.author.id}, {item_category}' in notify_data):
				delete_message = await ctx.send(f'User <@{ctx.author.id}> is already on the notification list for item: {item_category}')
				try:
					await ctx.message.delete(delay = 10.0)
					await delete_message.delete(delay = 10.0)
				except Exception as e:
					print('Deleting Message failed. Who cares.')
			else:
				if os.stat('notifyFile.txt').st_size == 0:
					notifyFile.write(f'{ctx.author.name}, {ctx.author.id}, {item_category}')
				else:
					notifyFile.write(f'\n{ctx.author.name}, {ctx.author.id}, {item_category}')
					delete_message = await ctx.send(f'User <@{ctx.author.id}> has been added to the notification list for item: {item_category}')
					try:
						await ctx.message.delete(delay = 10.0)
						await delete_message.delete(delay = 10.0)
					except Exception as e:
						print('Deleting Message failed. Who cares.')
		notifyFile.close()

#remove from notify list command
@bot.command(name = 'remove', help = 'Removes user from notification list for specified item')
async def notify(ctx, item_category):
	#only allow users to add themselves to a notification list for items that are currently being tracked.
	#this list must be updated every time a new item category is added to items.txt
	if (item_category not in ('3080', '5900X')):
		delete_message = await ctx.send(f"User <@{ctx.author.id}> the item {item_category} doesn't exist.")
		await ctx.message.delete(delay = 10.0)
		await delete_message.delete(delay = 10.0) 
	else:
		with open('notifyFile.txt', 'r+') as notifyFile:
			notify_data = notifyFile.read()
			#removes the user from the notification list if they are on the list
			if (f'{ctx.author.name}, {ctx.author.id}, {item_category}' not in notify_data):
				delete_message = await ctx.send(f'User <@{ctx.author.id}> is not currently on the notification list for item: {item_category}')
				try:
					await ctx.message.delete(delay = 10.0)
					await delete_message.delete(delay = 10.0)
				except Exception as e:
					print('Deleting Message failed. Who cares.')
			else:
				for num, line in enumerate(notifyFile, 1):
					if (f'{ctx.author.name}, {ctx.author.id}, {item_category}' in line):
						notifyFile.write(line)
						delete_message = await ctx.send(f'User <@{ctx.author.id}> has been removed from the notification list for item: {item_category}')
						try:
							await ctx.message.delete(delay = 10.0)
							await delete_message.delete(delay = 10.0)
						except Exception as e:
							print('Deleting Message failed. Who cares.')
		notifyFile.close()

#send the user the current item list
@bot.command(name = 'items', help = 'Sends the user the current item list')
async def items(ctx):
	with open('notifyFile.txt', 'r') as notifyFile:
		await ctx.author.send(notifyFile)
		try:
			await ctx.message.delete(delay = 10.0)
		except Exception as e:
			print('Deleting Message failed. Who cares.')
	notifyFile.close()

#custom help command. sends help embed to DM instead of in channel
@bot.command(name = 'help', help = 'Displays this message')
async def help(ctx):
	help_embed=discord.Embed(title="Help Message", description="All commands are prefixed with %. All commands are case-insensitive.")
	help_embed.add_field(name="dm", value="DMs the user their username + user number", inline=False)
	help_embed.add_field(name="help", value="Displays this message", inline=False)
	help_embed.add_field(name="id", value="DM's the user their user ID", inline=False)
	help_embed.add_field(name="items", value="Sends the user the current item list", inline=False)
	help_embed.add_field(name="logout", value="Disconnect command. Calling restricted", inline=False)
	help_embed.add_field(name="notify", value="Adds user to notification list for the specified item", inline=False)
	help_embed.add_field(name="remove", value="Removes user from notification list for the specified item", inline=False)
	help_embed.set_footer(text="Message Tristan for help")
	await ctx.author.send(embed=help_embed)
	try:
		await ctx.message.delete(delay = 10.0)
	except Exception as e:
		print('Message failed to delete. Oh well.')
	

bot.loop.create_task(status_task())
bot.loop.create_task(stock_task())
bot.run(TOKEN)