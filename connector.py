import imaplib
import email
from email.header import decode_header
import base64
from bs4 import BeautifulSoup
import re
import traceback
from typing import Union
import codecs
import strip_markdown

from functions import from_hex

class MailConnector():
	def __init__(self, login: str, password: str, imap_server: str):
		self.login = login
		self.password = password
		self.imap_server = imap_server
	
	def connect(self) -> Union[bool, tuple[bool, str]]:
		try:
			imap = imaplib.IMAP4_SSL(self.imap_server)
			imap.login(self.login, self.password)
			self.imap = imap
			return True
		except Exception as e:
			return (False, str(e))

	def get_unseen_mails(self) -> Union[tuple, list[str]]:
		self.imap.select("INBOX")
		m = self.imap.uid('search', "UNSEEN", "ALL")
		if m[0] == 'OK':
			return list(m[1][0].decode().split())
		else:
			return (False, m)

	def get_inbox_len(self) -> int:
		self.imap.select('INBOX')
		c = self.imap.uid('search', None, 'ALL')
		try:
			return int(list(c[1][0].decode().split())[-1])
		except:
			return int(list(c[1][0].split())[-1])

	def get_mail_text(self, mail_id: Union[bytes, str], edit: bool = True) -> tuple[bool, tuple]:
		try:
			self.imap.select("INBOX")
			res, msg = self.imap.uid('fetch', mail_id, '(RFC822)')
			msg = email.message_from_bytes(msg[0][1])
			sender = email.utils.parseaddr(msg['from'])[1]
			if msg["Subject"] == None:
				header = '[Без темы]'
			else:
				try:
					header = decode_header(msg["Subject"])[0][0].decode()
				except:
					header = decode_header(msg["Subject"])[0][0]

			if msg.is_multipart() == True:
				sp = []
				codes = []
				for part in msg.walk():
				    if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'plain':
				        sp.append(part.get_payload())
				        codes.append(part['Content-Transfer-Encoding'])
			else:
				sp = [msg.get_payload()]
				codes = [msg['Content-Transfer-Encoding']]
			text = ''
			t = ''
			for i in range(len(sp)):
				s = sp[i]
				try:
					if codes[i] == 'base64':
						text += BeautifulSoup(base64.b64decode(s), features="lxml").get_text()
						t+=base64.b64decode(s)
					else:
						text += BeautifulSoup(from_hex(s), features="lxml").get_text()
						t+=from_hex(s)
				except:
					text += BeautifulSoup(s, features="lxml").get_text()
					t+=s
			#print(t)
			if not edit:
				return t 
			text = re.sub('(\n){1,}', '\n', text)
			text = strip_markdown.strip_markdown(text)
			header = header.replace('&', '&amp;')
			header = header.replace('<', '&lt;')
			header = header.replace('>', '&gt;')
			text = text.replace('\xa0', ' ')
			text = text.replace('\n>', '')
			text = text.replace('\r>', '')
			text = text.replace('\r', '')
			text = text.replace('&', '&amp;')
			text = text.replace('<', '&lt;')
			text = text.replace('>', '&gt;')
			return (True, (header, text, sender))
		except Exception as e:
			return (False, (traceback.format_exc(),))

	def close(self):
		self.imap.close()
		self.imap.logout()
