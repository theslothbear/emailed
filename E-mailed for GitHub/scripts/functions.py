import codecs

def from_hex(s: str) -> str:
	HEX = '0123456789ABCDEF'
	res = ''
	is_first = True
	for el in s.split('='):
		if is_first:
			is_first = False
			el_res = ''
			el2 = el
			for t in el2:
				el_res+= t.encode('utf-8').hex()
			res+=el_res
		else:
			el2 = ''
			el_res = ''
			if len(el) > 2:
				el2 = el[2:]
				for t in el2:
					el_res+= t.encode('utf-8').hex()
			res+=el[0:2]+el_res
	res = res.replace('\r', '').replace('\n', '')
	fh = codecs.decode(res, 'hex').decode('utf-8')
	return fh