from telebot import types

main_menu_markup = types.InlineKeyboardMarkup()
main_menu_markup.add(types.InlineKeyboardButton(text='➕Добавить почту', callback_data='add_mail'))
main_menu_markup.add(types.InlineKeyboardButton(text='✏Управление почтами', callback_data='my_mails'))
main_menu_markup.add(types.InlineKeyboardButton(text='⚙Настройки', callback_data='settings'))
main_menu_markup.add(types.InlineKeyboardButton(text='❓Ключи авторизации', url='https://theslothbear-emailed-server-cae5.twc1.net/keys'), types.InlineKeyboardButton(text='📰E-Mailed News', url='https://t.me/e_mailed'))
main_menu_markup.add(types.InlineKeyboardButton(text='🛠Техподдержка', url='https://t.me/slbdev'), types.InlineKeyboardButton(text='💻Исходный код', url='https://github.com/theslothbear'))

settings_markup = types.InlineKeyboardMarkup()
settings_markup.add(types.InlineKeyboardButton(text='Язык: 🇷🇺[RU]', callback_data='change_lang'))
settings_markup.add(types.InlineKeyboardButton(text='🏴Чёрный список', callback_data='blacklist'))
settings_markup.add(types.InlineKeyboardButton(text='🤖Токен GigaChat', callback_data='gigachat_token'))
settings_markup.add(types.InlineKeyboardButton(text='🔙Назад', callback_data='menu'))