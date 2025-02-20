import asyncio
import telebot
import sqlite3
import traceback
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import datetime
import gigachat

from connector import MailConnector
from config import VERSION, ADMIN_ID, TOKEN, SERVERS, URL, IMAGE, MAX_FREE_MAILS

bot = AsyncTeleBot(TOKEN)

connect = sqlite3.connect('testmailed.db', check_same_thread = False)
cursor = connect.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS all_users(
	user_id INTEGER
	)
""")
connect.commit()
cursor.execute("""CREATE TABLE IF NOT EXISTS mails(
	user_id INTEGER,
	login TEXT,
	password TEXT,
	imap_server TEXT
	)
""")
connect.commit()
cursor.execute("""CREATE TABLE IF NOT EXISTS last_ids(
	user_id INTEGER,
	login TEXT,
	last_mail_id INTEGER
	)
""")
connect.commit()
cursor.execute("""CREATE TABLE IF NOT EXISTS special_mail_ids(
	login TEXT,
	m_id INTEGER
	)
""")
connect.commit()
cursor.execute("""CREATE TABLE IF NOT EXISTS tokens(
	user_id INTEGER,
	token TEXT
	)
""")
connect.commit()


@bot.message_handler(commands=['start'])
async def start_func(message):
	try:
		await bot.delete_message(message.from_user.id, message.message.message_id)
	except:
		pass
	if cursor.execute("SELECT * FROM all_users WHERE user_id=?", (message.from_user.id,)).fetchone() == None:
		cursor.execute("INSERT INTO all_users VALUES(?);", [message.from_user.id])
		connect.commit()

	from markups import main_menu_markup 
	await bot.send_photo(message.from_user.id, IMAGE, f'🏠*Главное меню E-Mailed (v.{VERSION})*\n\n_Используйте кнопки ниже для навигации_', parse_mode='markdown', reply_markup=main_menu_markup)

@bot.message_handler(commands=['remove'])
async def remove_keyboard(message):
	await bot.send_message(message.from_user.id, '*🧹Клавиатура очищена*', reply_markup=types.ReplyKeyboardRemove(), parse_mode='markdown')

@bot.message_handler(commands=['startparsing'])
async def start_parsing(message):
	if message.from_user.id == ADMIN_ID:
		await parsing()

async def parsing():
	while True:
		records = cursor.execute("SELECT * FROM mails").fetchall()
		for row in records:
			try:
				mail = MailConnector(row[1], row[2], row[3])
				c = mail.connect()
				if c == True:
					#m_ids = mail.get_unseen_mails()
					last_m_id = cursor.execute("SELECT * FROM last_ids WHERE user_id=? AND login=?", [row[0], row[1]]).fetchone()
					if last_m_id == None:
						print('Чего? Как чел залогинен, но не залогинен?')
						m_id = 0
					else:
						m_id = last_m_id[2]

					m = cursor.execute("SELECT * FROM tokens WHERE user_id=?", (row[0],)).fetchone()
					if m == None:
						key = 'none'
					else:
						key = m[1]
					while True:
						m_id += 1
						mail_text = mail.get_mail_text(str(m_id))
						if mail_text[0] == True:
							header, text, sender = mail_text[1][0], mail_text[1][1], mail_text[1][2]
							if len(text) >= 3840:
								text = text[:3840] + ' ...\n<i>Текст письма обрезан из-за большой длины</i>'
							if text == '':
								text = '<i>Пустое сообщение</i>'

							mail_markup = types.InlineKeyboardMarkup()
							webApp1 = types.WebAppInfo(f"{URL}/mail?l={row[1]}&p={row[2]}&i={row[3]}&mid={m_id}")
							webApp2 = types.WebAppInfo(f"{URL}/retell?l={row[1]}&p={row[2]}&i={row[3]}&mid={m_id}&key={key}")
							
							mail_markup.add(types.InlineKeyboardButton(text='📔Открыть письмо', web_app=webApp1), types.InlineKeyboardButton(text='🤖Пересказать', web_app=webApp2))
							mes = await bot.send_message(row[0], f'✉ <b>{header}</b>\n👤 <i>{sender}</i>\n<blockquote expandable>{text}</blockquote>', parse_mode='html', link_preview_options=types.LinkPreviewOptions(True), reply_markup=mail_markup)
							#print(mes)
							await asyncio.sleep(2.0)
						else:
							if m_id - 1 != last_m_id:
								cursor.execute("DELETE FROM last_ids WHERE user_id=? AND login=?", [row[0], row[1]])
								connect.commit()
								cursor.execute("INSERT INTO last_ids VALUES(?,?,?);", [row[0], row[1], m_id-1])
								connect.commit()
							#print(mail_text)
							break

					mail.close()
				else:
					print(c)
					cursor.execute("DELETE FROM mails WHERE user_id=? AND login=?", [row[0], row[1]])
					connect.commit()
					await bot.send_message(row[0], f'*❌Не удалось войти в аккаунт почты {row[1]}*\n\nПопробуйте привязать почту еще раз. Если проблема сохраняется, обратитесь в тех.поддержку — @slbdev', parse_mode='markdown')
					await asyncio.sleep(2.0)

			except Exception as e:
				print('Ошибка при парсинге: ' + traceback.format_exc())
		
		await asyncio.sleep(15.0)

@bot.message_handler(content_types=['web_app_data'])
async def hand(message):
	s = message.web_app_data.data
	try:
		await bot.delete_message(message.from_user.id, message.message_id)
	except:
		pass
	if s[:5] == '!AUTH':
		s = s[5:]
		sp = list(s.split(' '))
		if len(sp) == 3 and (not '<' in sp[0]) and (not '>' in sp[0]) and (not '<' in sp[1]) and (not '>' in sp[1]) and (not '&' in sp[1]) and (not '&' in sp[0]):
			records = cursor.execute("SELECT * FROM mails WHERE user_id=?", (message.from_user.id,)).fetchall()
			if len(records) >= MAX_FREE_MAILS:
				await bot.send_message(message.from_user.id, f'📛Достигнут *лимит* привязанных *почт: {MAX_FREE_MAILS}*', reply_markup=types.ReplyKeyboardRemove(), parse_mode='markdown')
				return

			server = sp[2]
			mail = MailConnector(sp[0], sp[1], server)
			if mail.connect() == True:
				last_id = mail.get_inbox_len()
				cursor.execute("DELETE FROM mails WHERE user_id=? AND login=?", [message.from_user.id, sp[0]])
				connect.commit()
				cursor.execute("INSERT INTO mails VALUES(?,?,?,?);", [message.from_user.id, sp[0], sp[1], server])
				connect.commit()
				cursor.execute("DELETE FROM last_ids WHERE user_id=? AND login=?", [message.from_user.id, sp[0]])
				connect.commit()
				cursor.execute("INSERT INTO last_ids VALUES(?,?,?);", [message.from_user.id, sp[0], last_id])
				connect.commit()
				await bot.send_message(message.from_user.id, f'*✅Почта {sp[0]} успешно привязана*', reply_markup=types.ReplyKeyboardRemove(), parse_mode='markdown')
				await my_mails_func(message)

			else:
				await bot.send_message(message.from_user.id, '*❌Не удалось привязать почту*: неверный адрес email или пароль.\n\n👉Обратите внимание, что необходимо ввести *не пароль от почты*, а специально сгенерированный 🔐*ключ*.\n\n[Пример для почты Yandex](https://yandex.ru/support/id/ru/authorization/app-passwords.html)', parse_mode='markdown', link_preview_options=types.LinkPreviewOptions(True))
		else:
			await bot.send_message(message.from_user.id, '*❌Не удалось привязать почту*: неверный формат ввода.', parse_mode='markdown')
	
	elif s[:5] == '!SEND':
		row = cursor.execute("SELECT * FROM mails WHERE user_id=? AND login=?", [message.from_user.id, s[5:]]).fetchone()
		flag_sended = False
		try:
			mail = MailConnector(row[1], row[2], row[3])
			c = mail.connect()
			if c == True:
				#m_ids = mail.get_unseen_mails()
				last_m_id = cursor.execute("SELECT * FROM last_ids WHERE user_id=? AND login=?", [row[0], row[1]]).fetchone()
				if last_m_id == None:
					print('Чего? Как чел залогинен, но не залогинен?')
					m_id = 0
				else:
					m_id = last_m_id[2]

				m = cursor.execute("SELECT * FROM tokens WHERE user_id=?", (row[0],)).fetchone()
				if m == None:
					key = 'none'
				else:
					key = m[1]
				while True:
					m_id += 1
					mail_text = mail.get_mail_text(str(m_id))
					if mail_text[0] == True:
						header, text, sender = mail_text[1][0], mail_text[1][1], mail_text[1][2]
						if len(text) >= 3840:
							text = text[:3840] + ' ...\n<i>Текст письма обрезан из-за большой длины</i>'
						if text == '':
							text = '<i>Пустое сообщение</i>'

						mail_markup = types.InlineKeyboardMarkup()
						webApp1 = types.WebAppInfo(f"{URL}/mail?l={row[1]}&p={row[2]}&i={row[3]}&mid={m_id}")
						webApp2 = types.WebAppInfo(f"{URL}/retell?l={row[1]}&p={row[2]}&i={row[3]}&mid={m_id}&key={key}")
						mail_markup.add(types.InlineKeyboardButton(text='📔Открыть письмо', web_app=webApp1), types.InlineKeyboardButton(text='🤖Пересказать', web_app=webApp2))
						mes = await bot.send_message(row[0], f'✉ <b>{header}</b>\n👤 <i>{sender}</i>\n<blockquote expandable>{text}</blockquote>', parse_mode='html', link_preview_options=types.LinkPreviewOptions(True), reply_markup=mail_markup)
						#print(mes)
						flag_sended = True
						await asyncio.sleep(2.0)
					else:
						if m_id - 1 != last_m_id:
							cursor.execute("DELETE FROM last_ids WHERE user_id=? AND login=?", [row[0], row[1]])
							connect.commit()
							cursor.execute("INSERT INTO last_ids VALUES(?,?,?);", [row[0], row[1], m_id-1])
							connect.commit()
						#print(mail_text)
						break

				mail.close()
				if not flag_sended:
					await bot.send_message(row[0], '*🔕Новых писем нет*', parse_mode='markdown', reply_markup=types.ReplyKeyboardRemove())
			else:
				print(c)
				cursor.execute("DELETE FROM mails WHERE user_id=? AND login=?", [row[0], row[1]])
				connect.commit()
				await bot.send_message(row[0], f'*❌Не удалось войти в аккаунт почты {row[1]}*\n\nПопробуйте привязать почту еще раз. Если проблема сохраняется, обратитесь в тех.поддержку — @slbdev', parse_mode='markdown')
				await asyncio.sleep(2.0)

		except Exception as e:
			print('Ошибка при парсинге: ' + traceback.format_exc())

	elif s[:5] == '!GIGA':
		s = s[5:]
		try:
			giga = gigachat.GigaChat(credentials=s, verify_ssl_certs=False)
			giga.get_token()
			#print(giga.get_token())
			cursor.execute("DELETE FROM tokens WHERE user_id=?", (message.from_user.id,))
			connect.commit()
			cursor.execute("INSERT INTO tokens VALUES(?,?)", [message.from_user.id, s])
			connect.commit()
			await bot.send_message(message.from_user.id, '*✅Токен успешно изменён!* Теперь вы можете пользоваться *пересказом писем* от нейросети🤖', parse_mode='markdown', reply_markup=types.ReplyKeyboardRemove())
		except:
			await bot.send_message(message.from_user.id, '*❌Введённый токен неверен*. Попробуйте ещё раз', parse_mode='markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'menu')
async def menu_func(call):
	try:
		await bot.delete_message(call.from_user.id, call.message.message_id)
	except:
		pass
	from markups import main_menu_markup 
	await bot.send_photo(call.from_user.id, IMAGE, f'🏠*Главное меню E-Mailed (v.{VERSION})*\n\n_Используйте кнопки ниже для навигации_', parse_mode='markdown', reply_markup=main_menu_markup)

@bot.callback_query_handler(func=lambda call: call.data == 'add_mail')
async def add_mail_func(call):
	records = cursor.execute("SELECT * FROM mails WHERE user_id=?", (call.from_user.id,)).fetchall()
	if len(records) >= MAX_FREE_MAILS:
		await bot.send_message(call.from_user.id, f'📛Достигнут *лимит* привязанных *почт: {MAX_FREE_MAILS}*', reply_markup=types.ReplyKeyboardRemove(), parse_mode='markdown')
		return
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
	webapp_login = types.WebAppInfo(f'{URL}/addmail')
	keyboard.add(types.KeyboardButton(text='➕Добавить почту', web_app=webapp_login))

	m = await bot.send_message(call.from_user.id, '*🌐Используйте кнопку ниже* для авторизации👇\n\n/remove _для отмены_', reply_markup=keyboard, parse_mode='markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'my_mails')
async def my_mails_func(call):
	try:
		await bot.delete_message(call.from_user.id, call.message.message_id)
	except:
		pass
	records = cursor.execute("SELECT * FROM mails WHERE user_id=?", (call.from_user.id,)).fetchall()
	my_mails_markup = types.InlineKeyboardMarkup()
	flag_added = False
	for row in records:
		spec_id = cursor.execute("SELECT * FROM special_mail_ids WHERE login=?", (row[1],)).fetchone()
		if spec_id == None:
			rec = cursor.execute("SELECT * FROM special_mail_ids").fetchall()
			if rec == []:
				last_rec_id = 0
			else:
				print(rec)
				last_rec_id = int(rec[-1][1])
			cursor.execute("INSERT INTO special_mail_ids VALUES(?,?);", [row[1], last_rec_id+1])
			connect.commit()
			spec_id = last_rec_id+1
		else:
			spec_id = spec_id[1]
		my_mails_markup.add(types.InlineKeyboardButton(text=f'{row[1]}', callback_data=f'M_{spec_id}'))
		flag_added = True
	if not flag_added:
		my_mails_markup.add(types.InlineKeyboardButton(text='➕Добавить почту', callback_data='add_mail'))
	my_mails_markup.add(types.InlineKeyboardButton(text='🔙Назад', callback_data='menu'))
	await bot.send_message(call.from_user.id, '*📧Привязанные почты*', reply_markup=my_mails_markup, parse_mode='markdown')

@bot.callback_query_handler(func=lambda call: call.data[:2] == 'M_')
async def mail_edit_func(call):
	spec_id = int(call.data[2:])
	login = cursor.execute("SELECT * FROM special_mail_ids WHERE m_id=?", (spec_id,)).fetchone()[0]
	m = cursor.execute("SELECT * FROM mails WHERE user_id=? AND login=?", [call.from_user.id, login]).fetchone()
	if m == None:
		await bot.send_message(call.from_user.id, f'❌Ошибка: нет доступа к почте {login}')
	else:
		last_m_id = cursor.execute("SELECT * FROM last_ids WHERE user_id=? AND login=?", [call.from_user.id, login]).fetchone()
		if last_m_id == None:
			print('Чего? Как чел залогинен, но не залогинен? M_ version')
			m_id = 0
		else:
			m_id = last_m_id[2]
		mail_edit_markup = types.InlineKeyboardMarkup()
		mail_edit_markup.add(types.InlineKeyboardButton(text='♻Инициировать парсинг', callback_data=f'status_{spec_id}'))
		#mail_edit_markup.add(types.InlineKeyboardButton(text='♻Инициировать парсинг', web_app=types.WebAppInfo(f'{URL}/parse?login={m[1]}&pass={m[2]}&imap={m[3]}&mail_id={m_id}')))
		mail_edit_markup.add(types.InlineKeyboardButton(text='🏴Чёрный список', callback_data=f'blacklist_{spec_id}'), types.InlineKeyboardButton(text='❌Отвязать почту', callback_data=f'delete_{spec_id}'))
		mail_edit_markup.add(types.InlineKeyboardButton(text='🔙Назад', callback_data=f'my_mails'))
		await bot.send_message(call.from_user.id, f'<b>⚒Управление почтой {login}</b>\n\n<b>🌐IMAP-server</b>: {m[3]}\n<b>🔐Ключ доступа</b>: <tg-spoiler>{m[2]}</tg-spoiler>', reply_markup=mail_edit_markup, parse_mode='html')

@bot.callback_query_handler(func=lambda call: call.data[:10] == 'blacklist_')
async def blacklist_func(call):
	await bot.answer_callback_query(call.id, 'Soon...', show_alert = True)

@bot.callback_query_handler(func=lambda call: call.data[:7] == 'delete_')
async def delete_mail_func(call):
	spec_id = int(call.data[7:])
	login = cursor.execute("SELECT * FROM special_mail_ids WHERE m_id=?", (spec_id,)).fetchone()[0]
	m = cursor.execute("SELECT * FROM mails WHERE user_id=? AND login=?", [call.from_user.id, login]).fetchone()
	if m == None:
		await bot.send_message(call.from_user.id, f'❌Ошибка: нет доступа к почте {login}')
	else:
		cursor.execute("DELETE FROM mails WHERE user_id=? AND login=?", [call.from_user.id, login])
		connect.commit()
		await bot.answer_callback_query(call.id, '✔Почта успешно откреплена', show_alert = True)
		await bot.delete_message(call.from_user.id, call.message.message_id)
		await my_mails_func(call)


@bot.callback_query_handler(func=lambda call: call.data[:7] == 'status_')
async def get_status(call):
	spec_id = int(call.data[7:])
	login = cursor.execute("SELECT * FROM special_mail_ids WHERE m_id=?", (spec_id,)).fetchone()[0]
	m = cursor.execute("SELECT * FROM mails WHERE user_id=? AND login=?", [call.from_user.id, login]).fetchone()
	if m == None:
		await bot.send_message(call.from_user.id, f'❌Ошибка: нет доступа к почте {login}')
	else:
		last_m_id = cursor.execute("SELECT * FROM last_ids WHERE user_id=? AND login=?", [call.from_user.id, login]).fetchone()
		if last_m_id == None:
			print('Чего? Как чел залогинен, но не залогинен? Status version')
			m_id = 0
		else:
			m_id = last_m_id[2]
		keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
		webapp_login = types.WebAppInfo(f'{URL}/parse?user_id={m[0]}&login={m[1]}&pass={m[2]}&imap={m[3]}&mail_id={m_id}')
		keyboard.add(types.KeyboardButton(text='♻Инициировать парсинг', web_app=webapp_login))

		m = await bot.send_message(call.from_user.id, '*🌐Используйте кнопку ниже* для инициирования парсинга👇\n\n/remove _для отмены_', reply_markup=keyboard, parse_mode='markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'settings')
async def settings(call):
	from markups import settings_markup
	await bot.send_photo(call.from_user.id, IMAGE, '*⚙Настройки*\n\n_Используйте кнопки ниже для навигации:_', parse_mode='markdown', reply_markup=settings_markup)


@bot.callback_query_handler(func=lambda call: call.data == 'gigachat_token')
async def gigachat_token(call):
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
	webapp_login = types.WebAppInfo(f'{URL}/change_token')
	keyboard.add(types.KeyboardButton(text='🔁Изменить токен', web_app=webapp_login))
	await bot.send_message(call.from_user.id, '*🌐Используйте кнопку ниже* для изменения вашего токена GigaChat👇\n\n/remove _для отмены_', reply_markup=keyboard, parse_mode='markdown')


asyncio.run(bot.polling(none_stop=True, interval=0))