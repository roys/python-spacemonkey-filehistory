import spacemonkeyconfig
import sqlite3
import os
import sys
import hashlib
import datetime
import smtplib
import email.mime.text

def md5_for_file(path, block_size=256*128, hr=False):
    '''
    Block size directly depends on the block size of your filesystem
    to avoid performances issues
    Here I have blocks of 4096 octets (Default NTFS)
    '''
    md5 = hashlib.md5()
    with open(path,'rb') as f: 
        for chunk in iter(lambda: f.read(block_size), b''): 
             md5.update(chunk)
    if hr:
        return md5.hexdigest()
    return md5.digest()

def send_mail(contents):
	mail = email.mime.text.MIMEText(contents)
	mail['Subject'] = 'Space Monkey file report'
	mail['From'] = spacemonkeyconfig.EMAIL_ADDRESS_FROM
	mail['To'] = spacemonkeyconfig.EMAIL_ADDRESS_TO

def main():
	print('Using Space Monkey path [%s].' % (spacemonkeyconfig.SPACE_MONKEY_PATH))
	print('Using SQLite file path [%s].' % (spacemonkeyconfig.SQLITE_FILE_PATH))

	if not os.path.exists(spacemonkeyconfig.SPACE_MONKEY_PATH):
		print ('Could not find Space Monkey path. Reporting and terminating program.')
		sys.exit(1)

	isFirstRun = False

	if not os.path.isfile(spacemonkeyconfig.SQLITE_FILE_PATH):
		print 'SQLite file doesn\' exist. File will be created.'
		isFirstRun = True

	send_mail('yay :)')
	connection = sqlite3.connect(spacemonkeyconfig.SQLITE_FILE_PATH)
	cursor = connection.cursor()
	cursor.execute('CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, name TEXT UNIQUE, deleted BOOLEAN DEFAULT FALSE, size INTEGER, hash TEXT, created DATETIME, modified DATETIME, added DATETIME, hash_change DATETIME, last_seen)')

	now = datetime.datetime.now()

	for root, dirs, files in os.walk(spacemonkeyconfig.SPACE_MONKEY_PATH):
		for name in files:
			path = os.path.join(root, name)
			name = path[len(SPACE_MONKEY_PATH):].decode('utf8')
			md5 = md5_for_file(path, 256*128, True)
			cursor.execute('SELECT hash FROM files WHERE name = ?', (name, ))
			row = cursor.fetchone()
			if row == None or row[0] != md5: # New or changed file
				size = os.path.getsize(path)
				created = datetime.datetime.fromtimestamp(os.path.getctime(path))
				modified = datetime.datetime.fromtimestamp(os.path.getmtime(path))
				if row == None: # New file
					cursor.execute('INSERT INTO files(name, size, hash, created, modified, added, hash_change, last_seen) VALUES(?, ?, ?, ?, ?, ?, ?, ?)', (name, size, md5, created, modified, now, now, now))
				elif row[0] != md5: # File contents has changed
					cursor.execute('UPDATE files SET size = ?, hash = ?, modified = ?, hash_change = ?, last_seen = ? WHERE name = ?', (size, md5, modified, now, now, name))
			else:
				cursor.execute('UPDATE files SET last_seen = ? WHERE name = ?', (now, name))

	connection.commit()
	connection.close()

if __name__ == '__main__':
	main()
