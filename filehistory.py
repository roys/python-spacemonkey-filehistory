import spacemonkeyconfig as cfg
import sqlite3
import os
import sys
import hashlib
import datetime
import smtplib
import email.mime.text
import time
import socket

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


def write_report(contents):
	millis = str(int(round(time.time() * 1000)))
	filename = cfg.FALLBACK_REPORT_PATH + 'spacemonkey_report-' + millis + '.txt'
	file = open(filename, 'w')
	file.write(contents)
	file.close()
	print('Wrote report to file [%s].' % (filename))


def send_report(contents):
	try:
		mail = email.mime.text.MIMEText(contents)
		mail['Subject'] = 'Space Monkey file report'
		mail['From'] = cfg.EMAIL_ADDRESS_FROM
		mail['To'] = cfg.EMAIL_ADDRESS_TO
		smtp = smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT)
		smtplib.SMTP.starttls(smtp)
		smtp.login(cfg.SMTP_USERNAME, cfg.SMTP_PASSWORD)
		smtp.sendmail(cfg.EMAIL_ADDRESS_FROM, [cfg.EMAIL_ADDRESS_TO], mail.as_string())
		smtp.quit()
	except socket.error as e:
		print e
		print 'Got socket error while trying to send mail. Will write report to file.'
		write_report(contents)


def main():
	print('Using Space Monkey path [%s].' % (cfg.SPACE_MONKEY_PATH))
	print('Using SQLite file path [%s].' % (cfg.SQLITE_FILE_PATH))

	if not os.path.exists(cfg.SPACE_MONKEY_PATH):
		send_report('Could not find Space Monkey path. Will not run program.')
		print ('Could not find Space Monkey path. Reporting and terminating program.')
		sys.exit(1)

	report = ''

	if not os.path.isfile(cfg.SQLITE_FILE_PATH):
		print 'SQLite file doesn\' exist. File will be created.'
		report += 'SQLite file doesn\' exist. File will be created.\n\n'
	
	connection = sqlite3.connect(cfg.SQLITE_FILE_PATH)
	cursor = connection.cursor()
	cursor.execute('CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, name TEXT UNIQUE, deleted BOOLEAN DEFAULT FALSE, size TEXT, hash TEXT, created DATETIME, modified DATETIME, added DATETIME, hash_change DATETIME, last_seen)')

	now = str(datetime.datetime.now())

	for root, dirs, files in os.walk(cfg.SPACE_MONKEY_PATH):
		for name in files:
			path = os.path.join(root, name)
			name = path[len(cfg.SPACE_MONKEY_PATH):].decode('utf8')
			md5 = md5_for_file(path, 256*128, True)
			cursor.execute('SELECT hash FROM files WHERE name = ?', (name, ))
			row = cursor.fetchone()
			if row == None or row[0] != md5: # New or changed file
				size = str(os.path.getsize(path))
				created = str(datetime.datetime.fromtimestamp(os.path.getctime(path)))
				modified = str(datetime.datetime.fromtimestamp(os.path.getmtime(path)))
				if row == None: # New file
					report += 'New file: ' + name + ', ' + size + ', ' + md5 + ', ' + created + ', ' + modified + ', ' + now + '\n'
					cursor.execute('INSERT INTO files(name, size, hash, created, modified, added, hash_change, last_seen) VALUES(?, ?, ?, ?, ?, ?, ?, ?)', (name, size, md5, created, modified, now, now, now))
				elif row[0] != md5: # File contents has changed
					report += 'Changed file: ' + name + ', ' + size + ', ' + md5 + ', ' + created + ', ' + modified + ', ' + now + '\n'
					cursor.execute('UPDATE files SET size = ?, hash = ?, modified = ?, hash_change = ?, last_seen = ?, deleted = ? WHERE name = ?', (size, md5, modified, now, now, 'FALSE', name))
			else:
				cursor.execute('UPDATE files SET last_seen = ?, deleted = ? WHERE name = ?', (now, 'FALSE', name))
	rows = cursor.execute('SELECT name, size, hash, created, modified, last_seen FROM files WHERE last_seen < ? AND deleted = ? ORDER BY name', (now, 'FALSE'))
	for row in rows:
		report += 'Deleted file: ' + str(row[0]) + ', ' + row[1] + ', ' + row[2] + ', ' + row[3] + ', ' + row[4] + ', ' + row[5]
		cursor.execute('UPDATE files SET deleted = ? WHERE name = ?', ('TRUE', row[0]))

	if report == '':
		report = 'No file changes.'
	
	send_report(report)
	connection.commit()
	connection.close()

if __name__ == '__main__':
	main()
