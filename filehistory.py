import sqlite3
import os
import sys
import hashlib
import datetime

SPACE_MONKEY_PATH = '/Users/roy/SpaceMonkey'
SPACE_MONKEY_PATH = '/Users/roy/SpaceMonkey/Photos/2012/2012-01-11-Ullplagg'
SQLITE_FILE_PATH = '/Users/roy/Google Drive/spacemonkey-filehistory.sql'

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

def main():
	print('Using Space Monkey path [%s].' % (SPACE_MONKEY_PATH))
	print('Using SQLite file path [%s].' % (SQLITE_FILE_PATH))

	if not os.path.exists(SPACE_MONKEY_PATH):
		print ('Could not find Space Monkey path. Terminating program.')
		sys.exit(1)

	isFirstRun = False

	if not os.path.isfile(SQLITE_FILE_PATH):
		print 'SQLite file doesn\' exist. File will be created.'
		isFirstRun = True

	connection = sqlite3.connect(SQLITE_FILE_PATH)
	cursor = connection.cursor()
	cursor.execute('CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, name TEXT UNIQUE, size INTEGER, hash TEXT, createdDateTime DATETIME, modifiedDateTime DATETIME, addedDateTime DATETIME, updatedDateTime DATETIME)')

	now = datetime.datetime.now()

	for root, dirs, files in os.walk(SPACE_MONKEY_PATH):
		for name in files:
			path = os.path.join(root, name)
			name = path[len(SPACE_MONKEY_PATH):].decode('utf8')
			size = os.path.getsize(path)
			md5 = md5_for_file(path, 256*128, True)
			created = datetime.datetime.fromtimestamp(os.path.getctime(path))
			modified = datetime.datetime.fromtimestamp(os.path.getmtime(path))
			cursor.execute('SELECT hash FROM files WHERE name = ?', (name, ))
			row = cursor.fetchone()
			if row == None: # New file
				cursor.execute('INSERT INTO files(name, size, hash, createdDateTime, modifiedDateTime, addedDateTime, updatedDateTime) VALUES(?, ?, ?, ?, ?, ?, ?)', (name, size, md5, created, modified, now, now))
			elif row[0] != md5: # File contents has changed
				cursor.execute('UPDATE files SET size = ?, hash = ?, modifiedDateTime = ?, updatedDateTime = ? WHERE name = ?', (size, md5, modified, now, name))
	
	connection.commit()
	connection.close()

if __name__ == '__main__':
	main()
