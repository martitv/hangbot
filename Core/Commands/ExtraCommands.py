import asyncio
from datetime import timedelta, datetime
from fractions import Fraction
import glob
import json
import os
import random
import threading
from urllib import parse, request
from bs4 import BeautifulSoup
from dateutil import parser
import hangups
import re
import requests
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot
from Libraries import Genius
#lunsj command
from html.parser import HTMLParser
import urllib.request, urllib.error, urllib.parse


reminders = []


@DispatcherSingleton.register
def count(bot, event, *args):
    words = ' '.join(args)
    count = UtilBot.syllable_count(words)
    bot.send_message(event.conv,
                     '"' + words + '"' + " has " + str(count) + (' syllable.' if count == 1 else ' syllables.'))


@DispatcherSingleton.register
def udefine(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Urbanly Define', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /udefine <word to search for> <optional: definition number [defaults to 1st]>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Define a word.')]
        bot.send_message_segments(event.conv, segments)
    else:
        api_host = 'http://urbanscraper.herokuapp.com/search/'
        num_requested = 0
        returnall = False
        if len(args) == 0:
            bot.send_message(event.conv, "Invalid usage of /udefine.")
            return
        else:
            if args[-1] == '*':
                args = args[:-1]
                returnall = True
            if args[-1].isdigit():
                # we subtract one here because def #1 is the 0 item in the list
                num_requested = int(args[-1]) - 1
                args = args[:-1]

            term = parse.quote('.'.join(args))
            response = requests.get(api_host + term)
            error_response = 'No definition found for \"{}\".'.format(' '.join(args))
            if response.status_code != 200:
                bot.send_message(event.conv, error_response)
            result = response.content.decode()
            result_list = json.loads(result)
            num_requested = min(num_requested, len(result_list) - 1)
            num_requested = max(0, num_requested)
            result = result_list[num_requested].get(
                'definition', error_response)
            if returnall:
                segments = []
                for string in result_list:
                    segments.append(hangups.ChatMessageSegment(string))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment(' '.join(args), is_bold=True),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment(result + ' [{0} of {1}]'.format(
                                num_requested + 1, len(result_list)))]
                bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def remind(bot, event, *args):
    # TODO Implement a private chat feature. Have reminders save across reboots?
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Remind', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /remind <optional: date [defaults to today]> <optional: time [defaults to an hour from now]> Message'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /remind'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /remind delete <index to delete>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Will post a message the date and time specified to the current chat. With no arguments, it\'ll list all the reminders.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if len(args) == 0:
            segments = [hangups.ChatMessageSegment('Reminders:', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            if len(reminders) > 0:
                for x in range(0, len(reminders)):
                    reminder = reminders[x]
                    reminder_timer = reminder[0]
                    reminder_text = reminder[1]
                    date_to_post = datetime.now() + timedelta(seconds=reminder_timer.interval)
                    segments.append(
                        hangups.ChatMessageSegment(
                            str(x + 1) + ' - ' + date_to_post.strftime('%m/%d/%y %I:%M%p') + ' : ' + reminder_text))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.pop()
                bot.send_message_segments(event.conv, segments)
            else:
                bot.send_message(event.conv, "No reminders are currently set.")
            return
        if args[0] == 'delete':
            try:
                x = int(args[1])
                x -= 1
            except ValueError:
                bot.send_message(event.conv, 'Invalid integer: ' + args[1])
                return
            if x in range(0, len(reminders)):
                reminder_to_remove_text = reminders[x][1]
                reminders[x][0].cancel()
                reminders.remove(reminders[x])
                bot.send_message(event.conv, 'Removed reminder: ' + reminder_to_remove_text)
            else:
                bot.send_message(event.conv, 'Invalid integer: ' + str(x + 1))
            return

        def send_reminder(bot, conv, reminder_time, reminder_text, loop):
            asyncio.set_event_loop(loop)
            bot.send_message(conv, reminder_text)
            for reminder in reminders:
                if reminder[0].interval == reminder_time and reminder[1] == reminder_text:
                    reminders.remove(reminder)

        args = list(args)
        date = str(datetime.now().today().date())
        time = str((datetime.now() + timedelta(hours=1)).time())
        set_date = False
        set_time = False
        index = 0
        while index < len(args):
            item = args[index]
            if item[0].isnumeric():
                if '/' in item or '-' in item:
                    date = item
                    args.remove(date)
                    set_date = True
                    index -= 1
                else:
                    time = item
                    args.remove(time)
                    set_time = True
                    index -= 1
            if set_date and set_time:
                break
            index += 1

        reminder_time = date + ' ' + time
        if len(args) > 0:
            reminder_text = ' '.join(args)
        else:
            bot.send_message(event.conv, 'No reminder text set.')
            return
        current_time = datetime.now()
        try:
            reminder_time = parser.parse(reminder_time)
        except (ValueError, TypeError):
            bot.send_message(event.conv, "Couldn't parse " + reminder_time + " as a valid date.")
            return
        if reminder_time < current_time:
            reminder_time = current_time + timedelta(hours=1)
        reminder_interval = (reminder_time - current_time).seconds
        reminder_timer = threading.Timer(reminder_interval, send_reminder,
                                         [bot, event.conv, reminder_interval, reminder_text, asyncio.get_event_loop()])
        reminders.append((reminder_timer, reminder_text))
        reminder_timer.start()
        bot.send_message(event.conv, "Reminder set for " + reminder_time.strftime('%B %d, %Y %I:%M%p'))


@DispatcherSingleton.register
def finish(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Finish', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /finish <lyrics to finish> <optional: * symbol to show guessed song>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Finish a lyric!')]
        bot.send_message_segments(event.conv, segments)
    else:
        showguess = False
        if args[-1] == '*':
            showguess = True
            args = args[0:-1]
        lyric = ' '.join(args)
        songs = Genius.search_songs(lyric)

        if len(songs) < 1:
            bot.send_message(event.conv, "I couldn't find your lyrics.")
        lyrics = songs[0].raw_lyrics
        anchors = {}

        lyrics = lyrics.split('\n')
        currmin = (0, UtilBot.levenshtein_distance(lyrics[0], lyric)[0])
        for x in range(1, len(lyrics) - 1):
            try:
                currlyric = lyrics[x]
                if not currlyric.isspace():
                    # Returns the distance and whether or not the lyric had to be chopped to compare
                    result = UtilBot.levenshtein_distance(currlyric, lyric)
                else:
                    continue
                distance = abs(result[0])
                lyrics[x] = lyrics[x], result[1]

                if currmin[1] > distance:
                    currmin = (x, distance)
                if currlyric.startswith('[') and currlyric not in anchors:
                    next = UtilBot.find_next_non_blank(lyrics, x)
                    anchors[currlyric] = lyrics[next]
            except Exception:
                pass
        next = UtilBot.find_next_non_blank(lyrics, currmin[0])
        chopped = lyrics[currmin[0]][1]
        found_lyric = lyrics[currmin[0]][0] + " " + lyrics[next][0] if chopped else lyrics[next][0]
        if found_lyric.startswith('['):
            found_lyric = anchors[found_lyric]
        if showguess:
            segments = [hangups.ChatMessageSegment(found_lyric),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(songs[0].name)]
            bot.send_message_segments(event.conv, segments)
        else:
            bot.send_message(event.conv, found_lyric)

        return


@DispatcherSingleton.register
def record(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Record', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record <text to record>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record date <date to show records from>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record list'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record search <search term>'),
                    hangups.ChatMessageSegment(
                        'Usage: /record strike'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Store/Show records of conversations. Note: All records will be prepended by: \"On the day of <date>,\" automatically. ')]
        bot.send_message_segments(event.conv, segments)
    else:
        import datetime

        global last_recorded, last_recorder
        directory = "Records" + "\\" + str(event.conv_id)
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = str(datetime.date.today()) + ".txt"
        file = None
        if ''.join(args) == "clear":
            file = open(directory + '\\' + filename, "a+")
            file.seek(0)
            file.truncate()
        elif ''.join(args) == '':
            file = open(directory + '\\' + filename, "a+")
            # If the mode is r+, it won't create the file. If it's a+, I have to seek to the beginning.
            file.seek(0)
            segments = [hangups.ChatMessageSegment(
                'On the day of ' + datetime.date.today().strftime('%B %d, %Y') + ':', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            for line in file:
                segments.append(
                    hangups.ChatMessageSegment(line))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        elif args[0] == "strike":
            if event.user.id_ == last_recorder:
                file = open(directory + '\\' + filename, "a+")
                file.seek(0)
                file_lines = file.readlines()
                if last_recorded is not None and last_recorded in file_lines:
                    file_lines.remove(last_recorded)
                file.seek(0)
                file.truncate()
                file.writelines(file_lines)
                last_recorded = None
                last_recorder = None
            else:
                bot.send_message(event.conv, "You do not have the authority to strike from the Record.")
        elif args[0] == "list":
            files = os.listdir(directory)
            segments = []
            for name in files:
                segments.append(hangups.ChatMessageSegment(name.replace(".txt", "")))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        elif args[0] == "search":
            args = args[1:]
            searched_term = ' '.join(args)
            escaped_args = []
            for item in args:
                escaped_args.append(re.escape(item))
            term = '.*'.join(escaped_args)
            term = term.replace(' ', '.*')
            if len(args) > 1:
                term = '.*' + term
            else:
                term = '.*' + term + '.*'
            foundin = []
            for name in glob.glob(directory + "\\" + '*.txt'):
                with open(name) as f:
                    contents = f.read()
                if re.match(term, contents, re.IGNORECASE | re.DOTALL):
                    foundin.append(name.replace(directory, "").replace(".txt", "").replace("\\", ""))
            if len(foundin) > 0:
                segments = [hangups.ChatMessageSegment("Found "),
                            hangups.ChatMessageSegment(searched_term, is_bold=True),
                            hangups.ChatMessageSegment(" in:"),
                            hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK)]
                for filename in foundin:
                    segments.append(hangups.ChatMessageSegment(filename))
                    segments.append(hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment("Couldn't find  "),
                            hangups.ChatMessageSegment(searched_term, is_bold=True),
                            hangups.ChatMessageSegment(" in any records.")]
                bot.send_message_segments(event.conv, segments)
        elif args[0] == "date":
            from dateutil import parser

            args = args[1:]
            try:
                dt = parser.parse(' '.join(args))
            except Exception as e:
                bot.send_message(event.conv, "Couldn't parse " + ' '.join(args) + " as a valid date.")
                return
            filename = str(dt.date()) + ".txt"
            try:
                file = open(directory + '\\' + filename, "r")
            except IOError:
                bot.send_message(event.conv, "No record for the day of " + dt.strftime('%B %d, %Y') + '.')
                return
            segments = [hangups.ChatMessageSegment('On the day of ' + dt.strftime('%B %d, %Y') + ':', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            for line in file:
                segments.append(hangups.ChatMessageSegment(line))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        else:
            file = open(directory + '\\' + filename, "a+")
            file.write(' '.join(args) + '\n')
            bot.send_message(event.conv, "Record saved successfully.")
            last_recorder = event.user.id_
            last_recorded = ' '.join(args) + '\n'
        if file is not None:
            file.close()


@DispatcherSingleton.register
def trash(bot, event, *args):
    bot.send_message(event.conv, "🚮")


@DispatcherSingleton.register
def spoof(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Spoof', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /spoof'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Who knows...')]
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('!!! CAUTION !!!', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('User ')]
        link = 'https://plus.google.com/u/0/{}/about'.format(event.user.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(event.user.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        segments.append(hangups.ChatMessageSegment(' has just been reporting to the NSA for attempted spoofing!'))
        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def flip(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Flip', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /flip <optional: number of times to flip>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Flips a coin.')]
        bot.send_message_segments(event.conv, segments)
    else:
        times = 1
        if len(args) > 0 and args[-1].isdigit():
            times = int(args[-1]) if int(args[-1]) < 1000000 else 1000000
        heads, tails = 0, 0
        for x in range(0, times):
            n = random.randint(0, 1)
            if n == 1:
                heads += 1
            else:
                tails += 1
        if times == 1:
            bot.send_message(event.conv, "Heads!" if heads > tails else "Tails!")
        else:
            bot.send_message(event.conv,
                             "Winner: " + (
                                 "Heads!" if heads > tails else "Tails!" if tails > heads else "Tie!") + " Heads: " + str(
                                 heads) + " Tails: " + str(tails) + " Ratio: " + (str(
                                 Fraction(heads, tails)) if heads > 0 and tails > 0 else str(heads) + '/' + str(tails)))


@DispatcherSingleton.register
def quote(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Quote', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /quote <optional: terms to search for> <optional: number of quote to show>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Shows a quote.')]
        bot.send_message_segments(event.conv, segments)
    else:
        USER_ID = "3696"
        DEV_ID = "ZWBWJjlb5ImJiwqV"
        QUERY_TYPE = "RANDOM"
        fetch = 0
        if len(args) > 0 and args[-1].isdigit():
            fetch = int(args[-1])
            args = args[:-1]
        query = '+'.join(args)
        if len(query) > 0:
            QUERY_TYPE = "SEARCH"
        url = "http://www.stands4.com/services/v2/quotes.php?uid=" + USER_ID + "&tokenid=" + DEV_ID + "&searchtype=" + QUERY_TYPE + "&query=" + query
        soup = BeautifulSoup(request.urlopen(url))
        if QUERY_TYPE == "SEARCH":
            children = list(soup.results.children)
            numQuotes = len(children)
            if numQuotes == 0:
                bot.send_message(event.conv, "Unable to find quote.")
                return

            if fetch > numQuotes - 1:
                fetch = numQuotes
            elif fetch < 1:
                fetch = 1
            bot.send_message(event.conv, "\"" +
                             children[fetch - 1].quote.text + "\"" + ' - ' + children[
                fetch - 1].author.text + ' [' + str(
                fetch) + ' of ' + str(numQuotes) + ']')
        else:
            bot.send_message(event.conv, "\"" + soup.quote.text + "\"" + ' -' + soup.author.text)
			

@DispatcherSingleton.register
def lunsj(bot, event, *args):

	usage = [	hangups.ChatMessageSegment('USAGE:', is_bold=True),
				hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
				hangups.ChatMessageSegment('/lunsj ifi (Informatikkafeen)'),
				hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
				hangups.ChatMessageSegment('/lunsj fred <dagens/vegetar/halal> (Frederikke spiseri)')
			]
	#Fredrikke cafe url
	urlFred = 'http://www.sio.no/wps/portal/!ut/p/c5/04_SB8K8xLLM9MSSzPy8xBz9CP0os3gDfwNvJ0dTP0NXAyNDA38TC3cDKADKR2LKmyDkidGNAzgS0h0Oci1-28HyuM3388jPTdUvyA2NMMgyUQQAAcWpkQ!!/dl3/d3/L0lDU0lKSWdrbUEhIS9JRFJBQUlpQ2dBek15cXchLzRCRWo4bzBGbEdpdC1iWHBBRUEhLzdfME8wS0JBNU4xRTBNSDJWMzVQMDAwMDAwMDAvN2x0YlQ2Mzk3MDAxOQ!!/?WCM_PORTLET=PC_7_0O0KBA5N1E0MH2V35P00000000000000_WCM&WCM_GLOBAL_CONTEXT=/wps/wcm/connect/migration/sio/mat+og+drikke/dagens+middag/frederikke+spiseri'
	#IFI cafe url
	urlIFI = 'http://www.sio.no/wps/portal/!ut/p/c5/04_SB8K8xLLM9MSSzPy8xBz9CP0os3gDfwNvJ0dTP0NXAyNDA38TC3cDKADKR2LKmyDkidGNAzgS0h0Oci1-28HyuM3388jPTdUvyA2NMMgyUQQAAcWpkQ!!/dl3/d3/L0lDU0lKSWdrbUEhIS9JRFJBQUlpQ2dBek15cXchLzRCRWo4bzBGbEdpdC1iWHBBRUEhLzdfME8wS0JBNU4xRTBNSDJWMzVQMDAwMDAwMDAvN2x0YlQ2Mzk3MDAxOQ!!/?WCM_PORTLET=PC_7_0O0KBA5N1E0MH2V35P00000000000000_WCM&WCM_GLOBAL_CONTEXT=/wps/wcm/connect/migration/sio/mat+og+drikke/dagens+middag/informatikkafeen'

	class MLStripper(HTMLParser):
		def __init__(self):
			super().__init__()
			self.reset()
			self.fed = []
			self.addFlag = False
		def handle_data(self, d):
			if self.addFlag:
				self.fed[-1] += d
				self.addFlag = False
			else:
				self.fed.append(d)
		#Fixes string splittig on the special character &
		def handle_entityref(self, ref):
			self.fed[-1] += self.unescape("&%s;" % ref)
			self.addFlag = True
		def get_data(self):
			return self.fed
			

	#Strips tags from given html
	def strip_tags(html):
		s = MLStripper()
		s.feed(html)
		return s.get_data()

	#Format function for fredrikke
	#Returns  a formatted string
	def format_fred(data):
		tmp = [x for x in data if x not in ['\n']]
		dict = {}
		iD = tmp.index("Dagens:")   #Finds index of Dagens/Vegetar/Halal
		iV = tmp.index("Vegetar: ")
		iH = tmp.index("Halal:")
		
		dict[tmp[:iV][0][:-1].lower()] = tmp[:iV][1:]    #Creates an entry in the dictionary with Dagens as key and listcontent uptil Vegetar-index as value
		dict[tmp[iV:][0][:-2].lower()] = tmp[iV:iH][1:]	 #Creates an entry in the dictionary with Vegetar as key and listcontent uptil Halal-index as value
		dict[tmp[iH:][0][:-1].lower()] = tmp[iH:][1:]    #Creates an entry in the dictionary with Halal as key and rest of listcontent as value
		
		segments = [	hangups.ChatMessageSegment(args[1].upper() + ":", is_bold=True),
						hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)
					]
		for i in dict[args[1].lower()]:
			segments.append(hangups.ChatMessageSegment(i))
			segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
		return segments

	#Used to translate current day to norwegian for dict-key purposes.
	enToNo = {'Monday':'Mandag', 'Tuesday':'Tirsdag', 'Wednesday':'Onsdag', 'Thursday':'Torsdag', 'Friday':'Fredag'}
	#Format function for fredrikke
	#Returns a formatted string.
	def format_ifi(data):
		#.encode('utf8', 'ignore') if characters bugs
		data = [x for x in data if x not in ['\n', '\xc2\xa0', '\xa0', 'Dagens: ', 'Vegetar:']]
		days = data[:5]
		food = data[5:]
		food.append("No veggie today D:") #Incase dagens and vegetar are the same on fridays.

		result = {}
		day = datetime.today().strftime("%A")
		for i in range(len(days)):
			result[days[i]] = (food[i*2], food[i*2+1]) #To foods pr day
			
		segments = [	hangups.ChatMessageSegment(enToNo[day], is_bold=True),
						hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
						hangups.ChatMessageSegment('\tDagens : ' + result[enToNo[day]][0]),
						hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
						hangups.ChatMessageSegment('\tVegetar: ' + result[enToNo[day]][1]),
					]
		return segments
			


	url = urlFred
	format_func = format_fred
	if len(args) < 1:
		bot.send_message_segments(event.conv, usage)
		return
	elif args[0].lower() == "ifi":
		url = urlIFI
		format_func = format_ifi
	elif args[0].lower() == "fred":
		if len(args) < 2 or args[1].lower() not in ['dagens', 'vegetar', 'halal']:
			bot.send_message_segments(event.conv, usage)
			return
		url = urlFred
		format_func = format_fred
		
	#Opens given url and returns html
	page = urllib.request.urlopen(url, timeout=10)
	#Html parsing
	soup = BeautifulSoup(page)

	#Finds the data we are looking for and feeds that to the formatting function.
	divtag = soup.find_all('div', {'class': 'sioArticleBodyText'})
	if len(divtag) > 0:
		tabletag = divtag[0].find_all('table')
		trtag = tabletag[0].find_all('tr')	
		text = str.join('',list(map(str,trtag)))
		data = strip_tags(text)
		bot.send_message_segments(event.conv, format_func(data))
	else:
		print("ERROR")
	page.close()

