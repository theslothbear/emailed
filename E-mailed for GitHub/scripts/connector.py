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

	def close(self):
		self.imap.close()
		self.imap.logout()

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


	def get_mail_text2(self, mail_id: Union[bytes, str]) -> dict[str]:
		self.imap.select("INBOX")
		res, msg_data = self.imap.uid('fetch', mail_id, '(RFC822)')
		
		if res != "OK" or not msg_data or msg_data == [None]:
			raise Exception(f'Failed to fetch mail')

		msg = email.message_from_bytes(msg_data[0][1])
		sender = email.utils.parseaddr(msg['from'])[1]
		
		header, encoding = decode_header(msg['Subject'])[0]
		if isinstance(header, bytes):
			header = header.decode(encoding if encoding else 'utf-8')
		
		if header is None:
			header = '[Без темы]'

		plain_text, html_text = '', ''
		if msg.is_multipart() == True:
			for part in msg.walk():
				content_type = part.get_content_type()
				print(content_type)
				content_disposition = str(part.get("Content-Disposition"))
				if "attachment" in content_disposition:
					continue
				
				if 'text/plain' in content_type:
					plain_text += self.decode_part_content(part)
				elif 'text/html' in content_type:
					html_text += self.decode_part_content(part)
		else:
			content_type = msg.get_content_type()

			content_disposition = str(msg.get("Content-Disposition"))
			if "attachment" in content_disposition:
				pass
			
			elif 'text/plain' in content_type:
				plain_text += self.decode_part_content(msg)
			elif 'text/html' in content_type:
				html_text += self.decode_part_content(msg)
				
		return {'sender': sender, 'header': header, 'plain': plain_text, 'html': html_text}

	def decode_part_content(self, part: email.message.Message) -> str:
		payload = part.get_payload(decode=True)
		if not payload:
			return ''
		
		charset = part.get_content_charset() or 'utf-8'
		try:
			return payload.decode(charset, errors='replace')
		except:
			return payload.decode('utf-8', errors='replace')

	def get_text_from_html(self, html_text: str) -> str:
		text = BeautifulSoup(html_text, features="lxml").get_text()

		text = text.replace('\xa0', ' ')
		text = text.replace('\n>', '')
		import re
		text = re.sub(r'\n{2,}', r'\n', text)
		text = text.replace('\r>', '')
		text = text.replace('\r', '')
		text = text.replace('\u200c', '')
		text = text.replace('\u200a', '')
		text = text.replace('&', '&amp;')
		text = text.replace('<', '&lt;')
		text = text.replace('>', '&gt;')

		return text.strip().lstrip()
